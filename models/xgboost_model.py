"""XGBoost による短期パターン学習"""

import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.model_selection import TimeSeriesSplit

from config import XGBOOST_DEFAULT_PARAMS, XGBOOST_N_SPLITS


class XGBoostPredictor:
    def __init__(self, params=None, horizon=5):
        self.params = params or XGBOOST_DEFAULT_PARAMS.copy()
        self.horizon = horizon
        self.model = None
        self.feature_importance = None
        self.val_residual_std = None

    def train(self, X, y):
        mask = ~(X.isna().any(axis=1) | y.isna())
        X_clean, y_clean = X[mask].copy(), y[mask].copy()
        if len(X_clean) < 50:
            raise ValueError(f"学習データ不足 ({len(X_clean)}行)")
        n_splits = min(XGBOOST_N_SPLITS, max(2, len(X_clean) // 60))
        tscv = TimeSeriesSplit(n_splits=n_splits)
        train_idx, val_idx = list(tscv.split(X_clean))[-1]
        X_train, y_train = X_clean.iloc[train_idx], y_clean.iloc[train_idx]
        X_val, y_val = X_clean.iloc[val_idx], y_clean.iloc[val_idx]
        # early_stoppingで過学習を防止
        fit_params = self.params.copy()
        n_est = fit_params.pop("n_estimators", 500)
        self.model = XGBRegressor(n_estimators=n_est, early_stopping_rounds=30, **fit_params)
        self.model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        self.feature_importance = pd.DataFrame({
            "feature": X_clean.columns,
            "importance": self.model.feature_importances_,
        }).sort_values("importance", ascending=False)
        val_pred = self.model.predict(X_val)
        self.val_residual_std = float(np.std(y_val - val_pred))
        return {"train_mae": float(np.mean(np.abs(y_train - self.model.predict(X_train)))),
                "val_mae": float(np.mean(np.abs(y_val - val_pred)))}

    def predict(self, X):
        if self.model is None:
            raise ValueError("モデル未学習")
        return self.model.predict(X.fillna(0))

    def get_feature_importance(self, top_n=15):
        if self.feature_importance is None:
            return pd.DataFrame(columns=["feature", "importance"])
        return self.feature_importance.head(top_n).copy()
