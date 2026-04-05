"""バックテストエンジン - Walk-Forward検証"""

import numpy as np
import pandas as pd

from models.prophet_model import ProphetPredictor
from models.xgboost_model import XGBoostPredictor
from data.feature_engineer import get_feature_columns, create_target_variables, add_technical_indicators
from config import (PROPHET_CHANGEPOINT_PRIOR, PROPHET_SEASONALITY_PRIOR,
                    XGBOOST_DEFAULT_PARAMS, ENSEMBLE_INITIAL_WEIGHTS)


class BacktestEngine:
    """Walk-Forward バックテストエンジン"""

    def __init__(self, train_ratio=0.7, horizon=5):
        self.train_ratio = train_ratio
        self.horizon = horizon
        self.results = None

    def run(self, price_df, weights=None, progress_callback=None):
        if weights is None:
            weights = ENSEMBLE_INITIAL_WEIGHTS.copy()

        feature_df = add_technical_indicators(price_df)
        df = create_target_variables(feature_df, [self.horizon])
        target_col = f"target_{self.horizon}d"
        feature_cols = get_feature_columns(df)

        valid_mask = ~df[target_col].isna()
        valid_df = df[valid_mask].copy()

        if len(valid_df) < 100:
            return {"error": "データが不足しています（最低100取引日必要）"}

        split_idx = int(len(valid_df) * self.train_ratio)
        test_df = valid_df.iloc[split_idx:]

        if len(test_df) < 10:
            return {"error": "テスト期間が短すぎます"}

        predictions = []
        step = max(1, len(test_df) // 40)
        total_steps = len(range(0, len(test_df), step))
        current_step = 0

        for i in range(0, len(test_df), step):
            if progress_callback:
                current_step += 1
                progress_callback(current_step, total_steps)

            test_point = test_df.iloc[i]
            train_end = test_df.index[i]
            train_data = df.loc[:train_end].iloc[:-1]
            if len(train_data) < 60:
                continue

            current_price = float(test_point["Close"])
            actual_return = float(test_point[target_col])
            actual_price = current_price * (1 + actual_return)

            # Prophet
            try:
                prophet = ProphetPredictor(
                    changepoint_prior_scale=PROPHET_CHANGEPOINT_PRIOR,
                    seasonality_prior_scale=PROPHET_SEASONALITY_PRIOR)
                prophet_df = pd.DataFrame({
                    "ds": train_data.index, "y": train_data["Close"].values})
                prophet.train(prophet_df)
                prophet.predict(periods=self.horizon)
                pp = prophet.get_forecast_point(1)
                prophet_price = pp["yhat"]
            except Exception:
                prophet_price = current_price

            # XGBoost
            try:
                xgb = XGBoostPredictor(
                    params=XGBOOST_DEFAULT_PARAMS.copy(), horizon=self.horizon)
                X_train = train_data[feature_cols].copy()
                y_train = train_data[target_col].copy()
                valid_train = ~y_train.isna()
                xgb.train(X_train[valid_train], y_train[valid_train])
                if xgb.model is not None:
                    xgb_return = float(xgb.predict(
                        pd.DataFrame([test_point[feature_cols]]))[0])
                    xgb_price = current_price * (1 + xgb_return)
                else:
                    xgb_price = current_price
            except Exception:
                xgb_price = current_price

            ensemble_price = (weights["prophet"] * prophet_price +
                              weights["xgboost"] * xgb_price)
            ensemble_return = (ensemble_price - current_price) / current_price

            # 方向一致度補正
            prophet_dir = 1 if prophet_price > current_price else -1
            xgb_dir = 1 if xgb_price > current_price else -1
            if prophet_dir == xgb_dir:
                ensemble_return *= 1.1
            else:
                ensemble_return *= 0.5
            ensemble_price = current_price * (1 + ensemble_return)

            predictions.append({
                "date": test_point.name,
                "current_price": current_price,
                "actual_price": actual_price,
                "actual_return": actual_return,
                "prophet_price": prophet_price,
                "xgboost_price": xgb_price,
                "ensemble_price": ensemble_price,
                "ensemble_return": ensemble_return,
                "direction_correct": (ensemble_return > 0) == (actual_return > 0),
            })

        if not predictions:
            return {"error": "予測を生成できませんでした"}

        results_df = pd.DataFrame(predictions)
        results_df["error"] = results_df["ensemble_price"] - results_df["actual_price"]
        results_df["abs_error"] = results_df["error"].abs()
        results_df["pct_error"] = results_df["error"] / results_df["actual_price"].replace(0, np.nan) * 100

        self.results = {
            "predictions": results_df,
            "metrics": self._calc_metrics(results_df),
            "train_size": split_idx,
            "test_size": len(test_df),
            "horizon": self.horizon,
        }
        return self.results

    def _calc_metrics(self, df):
        returns = df["ensemble_return"].values
        actual_returns = df["actual_return"].values
        mae = float(df["abs_error"].mean())
        rmse = float(np.sqrt((df["error"] ** 2).mean()))
        mape = float((df["abs_error"] / df["actual_price"].replace(0, np.nan) * 100).mean())
        direction_acc = float(df["direction_correct"].mean() * 100)

        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(252 / max(self.horizon, 1)))
        else:
            sharpe = 0.0

        cumulative = (1 + pd.Series(actual_returns)).cumprod()
        peak = cumulative.cummax()
        drawdown = (cumulative - peak) / peak
        max_drawdown = float(drawdown.min() * 100) if len(drawdown) > 0 else 0

        wins = sum(1 for r in returns if r > 0)
        win_rate = (wins / len(returns) * 100) if len(returns) > 0 else 0

        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 99.9

        return {
            "mae": mae, "rmse": rmse, "mape": mape,
            "direction_accuracy": direction_acc,
            "sharpe_ratio": sharpe, "max_drawdown": max_drawdown,
            "win_rate": win_rate, "profit_factor": min(profit_factor, 99.9),
            "total_predictions": len(df),
            "total_return": float((1 + pd.Series(returns)).prod() - 1) * 100,
        }
