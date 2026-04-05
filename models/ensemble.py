"""Prophet + XGBoost アンサンブル予測"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from config import (ENSEMBLE_INITIAL_WEIGHTS, ENSEMBLE_SMOOTHING_ALPHA,
                    ENSEMBLE_WEIGHT_CLAMP, XGBOOST_DEFAULT_PARAMS,
                    PROPHET_CHANGEPOINT_PRIOR, PROPHET_SEASONALITY_PRIOR)
from models.prophet_model import ProphetPredictor
from models.xgboost_model import XGBoostPredictor
from data.feature_engineer import get_feature_columns, create_target_variables


class EnsemblePredictor:
    def __init__(self, db, ticker):
        self.db = db
        self.ticker = ticker
        self.weights = db.load_weights(ticker)
        self.prophet = None
        self.xgboost = None
        self.last_result = None

    def train_and_predict(self, feature_matrix, horizon=5):
        df = create_target_variables(feature_matrix, [horizon])
        target_col = f"target_{horizon}d"
        current_price = float(df["Close"].iloc[-1])
        feature_cols = get_feature_columns(df)

        # Prophet
        prophet_params = self.db.load_model_params(self.ticker, "prophet")
        cp = (prophet_params or {}).get("changepoint_prior_scale", PROPHET_CHANGEPOINT_PRIOR)
        sp = (prophet_params or {}).get("seasonality_prior_scale", PROPHET_SEASONALITY_PRIOR)
        self.prophet = ProphetPredictor(changepoint_prior_scale=cp, seasonality_prior_scale=sp)
        prophet_df = pd.DataFrame({"ds": df.index, "y": df["Close"].values})
        self.prophet.train(prophet_df)
        self.prophet.predict(periods=horizon)
        pp = self.prophet.get_forecast_point(1)
        prophet_price, prophet_lower, prophet_upper = pp["yhat"], pp["yhat_lower"], pp["yhat_upper"]

        # XGBoost（バックテスト最良パラメータ → DB保存パラメータ → デフォルト）
        xgb_params = (self.db.get_best_backtest_params(self.ticker)
                      or self.db.load_model_params(self.ticker, "xgboost")
                      or XGBOOST_DEFAULT_PARAMS.copy())
        self.xgboost = XGBoostPredictor(params=xgb_params, horizon=horizon)
        X, y = df[feature_cols].copy(), df[target_col].copy()
        valid = ~y.isna()
        xgb_metrics = {"train_mae": None, "val_mae": None}
        try:
            xgb_metrics = self.xgboost.train(X[valid], y[valid])
        except ValueError:
            pass
        if self.xgboost.model is not None:
            xgb_return = float(self.xgboost.predict(X.iloc[[-1]])[0])
            xgb_price = current_price * (1 + xgb_return)
            xgb_std = self.xgboost.val_residual_std or 0.02
        else:
            xgb_price, xgb_std = current_price, 0.05

        # Ensemble（加重平均）
        w_p, w_x = self.weights["prophet"], self.weights["xgboost"]
        ensemble_price = w_p * prophet_price + w_x * xgb_price
        predicted_return = (ensemble_price - current_price) / current_price

        xgb_lower = ensemble_price - 2 * xgb_std * current_price
        xgb_upper = ensemble_price + 2 * xgb_std * current_price
        conf_lower = min(prophet_lower or xgb_lower, xgb_lower)
        conf_upper = max(prophet_upper or xgb_upper, xgb_upper)
        direction = "bullish" if predicted_return > 0.003 else ("bearish" if predicted_return < -0.003 else "neutral")

        # Save prediction
        try:
            self.db.save_prediction(
                ticker=self.ticker, prediction_date=datetime.now().strftime("%Y-%m-%d"),
                target_date=(datetime.now() + timedelta(days=horizon)).strftime("%Y-%m-%d"),
                horizon_days=horizon, current_price=current_price,
                predicted_price=ensemble_price, predicted_return=predicted_return,
                prophet_pred=prophet_price, xgboost_pred=xgb_price,
                confidence_lower=conf_lower, confidence_upper=conf_upper)
        except Exception:
            pass

        # 1年シナリオ予測（楽観・標準・悲観の3本線）
        self.prophet.predict(periods=252)
        scenario_df = self.prophet.get_future_series(252)

        fi = self.xgboost.get_feature_importance() if self.xgboost.model else pd.DataFrame()
        self.last_result = {
            "ensemble_price": ensemble_price, "prophet_price": prophet_price,
            "xgboost_price": xgb_price, "current_price": current_price,
            "predicted_return": predicted_return, "direction": direction,
            "confidence_lower": conf_lower, "confidence_upper": conf_upper,
            "weights": self.weights.copy(), "feature_importance": fi,
            "xgb_metrics": xgb_metrics,
            "prophet_components": self.prophet.get_components(),
            "scenario_forecast": scenario_df,
        }
        return self.last_result

    def update_weights_from_history(self):
        resolved = self.db.get_resolved_predictions(self.ticker, limit=30)
        if len(resolved) < 5:
            return None
        mae_p = float(np.mean(np.abs(resolved["prophet_pred"] - resolved["actual_price"])))
        mae_x = float(np.mean(np.abs(resolved["xgboost_pred"] - resolved["actual_price"])))
        eps = 1e-8
        raw_p, raw_x = 1.0 / (mae_p + eps), 1.0 / (mae_x + eps)
        total = raw_p + raw_x
        alpha = ENSEMBLE_SMOOTHING_ALPHA
        new_p = alpha * (raw_p / total) + (1 - alpha) * self.weights["prophet"]
        lo, hi = ENSEMBLE_WEIGHT_CLAMP
        new_p = max(lo, min(hi, new_p))
        new_x = 1.0 - new_p
        self.db.save_weights(self.ticker, new_p, new_x, mae_prophet=mae_p,
                             mae_xgboost=mae_x,
                             reason=f"MAE Prophet={mae_p:.4f}, MAE XGBoost={mae_x:.4f}")
        self.weights = {"prophet": new_p, "xgboost": new_x}
        return self.weights
