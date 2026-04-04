"""予測解決・実績比較エンジン"""

import numpy as np
from data.fetcher_yfinance import fetch_close_on_date


class PredictionTracker:
    def __init__(self, db):
        self.db = db

    def resolve_pending_predictions(self, ticker):
        unresolved = self.db.get_unresolved_predictions(ticker)
        count = 0
        for pred in unresolved:
            actual = fetch_close_on_date(ticker, pred["target_date"])
            if actual is None:
                continue
            cp = pred["current_price"]
            actual_return = (actual - cp) / cp
            error = pred["predicted_return"] - actual_return
            direction_correct = 1 if (pred["predicted_return"] >= 0) == (actual_return >= 0) else 0
            self.db.update_actual(pred["id"], actual, actual_return, error, direction_correct)
            count += 1
        return count

    def compute_metrics(self, ticker):
        resolved = self.db.get_resolved_predictions(ticker)
        if resolved.empty:
            return {"mae": 0, "rmse": 0, "mape": 0,
                    "directional_accuracy": 0, "total_predictions": 0}
        errors = resolved["error"].dropna()
        mae = float(errors.abs().mean())
        rmse = float(np.sqrt((errors ** 2).mean()))
        actuals = resolved["actual_return"].dropna()
        mape_raw = (errors.abs() / actuals.abs().replace(0, np.nan)).dropna()
        mape = float(mape_raw.mean()) if len(mape_raw) > 0 else 0
        dir_acc = float(resolved["direction_correct"].dropna().mean()) if "direction_correct" in resolved else 0
        return {"mae": mae, "rmse": rmse, "mape": mape,
                "directional_accuracy": dir_acc, "total_predictions": len(resolved)}
