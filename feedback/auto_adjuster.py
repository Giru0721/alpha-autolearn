"""Walk-forward パラメータ自動調整"""

import numpy as np
from config import (PROPHET_CHANGEPOINT_PRIOR, PROPHET_SEASONALITY_PRIOR,
                    XGBOOST_DEFAULT_PARAMS)
from feedback.tracker import PredictionTracker
from models.ensemble import EnsemblePredictor


class AutoAdjuster:
    def __init__(self, db):
        self.db = db

    def run_adjustment_cycle(self, ticker):
        tracker = PredictionTracker(self.db)
        resolved_count = tracker.resolve_pending_predictions(ticker)
        resolved = self.db.get_resolved_predictions(ticker, limit=50)
        if len(resolved) < 5:
            return None
        analysis = self._analyze_errors(resolved)
        prophet_params = self._adjust_prophet_params(ticker, analysis)
        xgboost_params = self._adjust_xgboost_params(ticker, analysis)
        ensemble = EnsemblePredictor(self.db, ticker)
        new_weights = ensemble.update_weights_from_history()
        metrics = tracker.compute_metrics(ticker)
        if metrics["total_predictions"] > 0:
            p_err = np.abs(resolved["prophet_pred"] - resolved["actual_price"]).dropna()
            x_err = np.abs(resolved["xgboost_pred"] - resolved["actual_price"]).dropna()
            e_err = np.abs(resolved["predicted_price"] - resolved["actual_price"]).dropna()
            self.db.save_error_snapshot(
                ticker=ticker,
                horizon_days=int(m.iloc[0]) if not (m := resolved["horizon_days"].mode()).empty else 5,
                mae=metrics["mae"], rmse=metrics["rmse"], mape=metrics["mape"],
                directional_accuracy=metrics["directional_accuracy"],
                total_predictions=metrics["total_predictions"],
                prophet_mae=float(p_err.mean()) if len(p_err) > 0 else 0,
                xgboost_mae=float(x_err.mean()) if len(x_err) > 0 else 0,
                ensemble_mae=float(e_err.mean()) if len(e_err) > 0 else 0)
        return {"resolved_count": resolved_count, "analysis": analysis,
                "prophet_params": prophet_params, "xgboost_params": xgboost_params,
                "new_weights": new_weights}

    def _analyze_errors(self, resolved):
        errors = resolved["error"].dropna()
        if errors.empty:
            return {"bias": 0, "volatility": "normal", "trend": "stable"}
        bias, std = float(errors.mean()), float(errors.std())
        mid = len(errors) // 2
        if mid > 0:
            first, second = float(errors.iloc[:mid].abs().mean()), float(errors.iloc[mid:].abs().mean())
            trend = "degrading" if second > first * 1.2 else ("improving" if second < first * 0.8 else "stable")
        else:
            trend = "stable"
        dir_acc = resolved["direction_correct"].dropna().mean() if "direction_correct" in resolved else 0.5
        return {"bias": bias, "std": std, "directional_accuracy": float(dir_acc),
                "trend": trend, "volatility": "high" if std > 0.05 else "normal"}

    def _adjust_prophet_params(self, ticker, analysis):
        current = self.db.load_model_params(ticker, "prophet") or {
            "changepoint_prior_scale": PROPHET_CHANGEPOINT_PRIOR,
            "seasonality_prior_scale": PROPHET_SEASONALITY_PRIOR}
        cp = current.get("changepoint_prior_scale", PROPHET_CHANGEPOINT_PRIOR)
        sp = current.get("seasonality_prior_scale", PROPHET_SEASONALITY_PRIOR)
        if analysis.get("directional_accuracy", 0.5) < 0.5 and analysis["trend"] == "degrading":
            cp, sp = min(0.5, cp * 1.5), max(1.0, sp * 0.8)
        elif analysis["trend"] == "degrading" and analysis.get("volatility") == "high":
            cp = max(0.001, cp * 0.7)
        params = {"changepoint_prior_scale": round(cp, 6), "seasonality_prior_scale": round(sp, 2)}
        self.db.save_model_params(ticker, "prophet", params)
        return params

    def _adjust_xgboost_params(self, ticker, analysis):
        current = self.db.load_model_params(ticker, "xgboost") or XGBOOST_DEFAULT_PARAMS.copy()
        md, ne, lr = current.get("max_depth", 6), current.get("n_estimators", 200), current.get("learning_rate", 0.05)
        ra, cs = current.get("reg_alpha", 0), current.get("colsample_bytree", 0.8)
        if analysis["trend"] == "degrading" and analysis.get("volatility") == "high":
            md, ra, cs = max(3, md - 1), ra + 0.1 if ra else 0.1, max(0.5, cs * 0.9)
        elif analysis["trend"] == "degrading":
            ne, lr = min(500, ne + 50), max(0.01, lr * 0.8)
        params = {"n_estimators": ne, "max_depth": md, "learning_rate": round(lr, 4),
                  "subsample": current.get("subsample", 0.8),
                  "colsample_bytree": round(cs, 3), "objective": "reg:squarederror", "random_state": 42}
        if ra > 0:
            params["reg_alpha"] = round(ra, 3)
        self.db.save_model_params(ticker, "xgboost", params)
        return params
