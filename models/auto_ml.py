"""自動機械学習エンジン - XGBoostハイパーパラメータ最適化

バックテスト結果から学習し、方向精度を最大化するパラメータを探索する。
Optuna不要 - 効率的なランダム探索 + ベイズ的ガイドで高速最適化。
"""

import random
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import TimeSeriesSplit

from data.feature_engineer import (
    get_feature_columns, create_target_variables, add_technical_indicators)
from config import XGBOOST_DEFAULT_PARAMS


# ===== 探索空間 =====
SEARCH_SPACE = {
    "max_depth": [3, 4, 5, 6, 7, 8],
    "learning_rate": [0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.1],
    "subsample": [0.6, 0.7, 0.8, 0.9, 1.0],
    "colsample_bytree": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    "reg_alpha": [0.0, 0.01, 0.05, 0.1, 0.3, 0.5, 1.0],
    "reg_lambda": [0.0, 0.5, 1.0, 2.0, 3.0, 5.0],
    "min_child_weight": [1, 3, 5, 7, 10],
    "gamma": [0.0, 0.05, 0.1, 0.2, 0.3],
    "n_estimators": [200, 300, 400, 500, 700, 1000],
}

# 実績あるプリセット（最初に試す）
PRESETS = [
    # バランス型
    {"max_depth": 5, "learning_rate": 0.03, "subsample": 0.8,
     "colsample_bytree": 0.7, "reg_alpha": 0.1, "reg_lambda": 1.0,
     "min_child_weight": 5, "gamma": 0.1, "n_estimators": 500},
    # 高速浅め
    {"max_depth": 3, "learning_rate": 0.05, "subsample": 0.9,
     "colsample_bytree": 0.8, "reg_alpha": 0.0, "reg_lambda": 1.0,
     "min_child_weight": 3, "gamma": 0.0, "n_estimators": 300},
    # 深め + 正則化
    {"max_depth": 7, "learning_rate": 0.01, "subsample": 0.7,
     "colsample_bytree": 0.6, "reg_alpha": 0.3, "reg_lambda": 2.0,
     "min_child_weight": 7, "gamma": 0.2, "n_estimators": 700},
    # シンプル低正則化
    {"max_depth": 4, "learning_rate": 0.05, "subsample": 0.9,
     "colsample_bytree": 0.9, "reg_alpha": 0.0, "reg_lambda": 0.5,
     "min_child_weight": 3, "gamma": 0.0, "n_estimators": 400},
    # 高正則化
    {"max_depth": 6, "learning_rate": 0.02, "subsample": 0.7,
     "colsample_bytree": 0.5, "reg_alpha": 0.5, "reg_lambda": 3.0,
     "min_child_weight": 10, "gamma": 0.3, "n_estimators": 500},
    # 中間バランス
    {"max_depth": 5, "learning_rate": 0.03, "subsample": 0.8,
     "colsample_bytree": 0.8, "reg_alpha": 0.05, "reg_lambda": 1.0,
     "min_child_weight": 5, "gamma": 0.05, "n_estimators": 500},
]


class AutoMLOptimizer:
    """XGBoostハイパーパラメータを方向精度最大化で最適化するエンジン"""

    def __init__(self, db, ticker, horizon=5):
        self.db = db
        self.ticker = ticker
        self.horizon = horizon
        self.best_params = None
        self.best_score = 0.0
        self.history = []

    def optimize(self, price_df, n_trials=30, progress_callback=None):
        """自動最適化を実行し、最適パラメータをDBに保存"""
        # --- データ準備 ---
        feature_df = add_technical_indicators(price_df)
        df = create_target_variables(feature_df, [self.horizon])
        target_col = f"target_{self.horizon}d"
        feature_cols = get_feature_columns(df)

        valid_mask = ~df[target_col].isna()
        valid_df = df[valid_mask].copy()
        if len(valid_df) < 100:
            return {"error": "データが不足しています（最低100取引日必要）"}

        X = valid_df[feature_cols].copy()
        y = valid_df[target_col].copy()
        mask = ~(X.isna().any(axis=1) | y.isna())
        X, y = X[mask], y[mask]
        if len(X) < 100:
            return {"error": "有効データ不足"}

        # --- 過去の最良パラメータをDBから取得 ---
        db_best = self.db.get_best_backtest_params(self.ticker, self.horizon)

        # --- 最適化ループ ---
        rng = random.Random(42)
        best_score = 0.0
        best_params = None

        for trial_idx in range(n_trials):
            if progress_callback:
                progress_callback(trial_idx + 1, n_trials)

            params = self._sample_params(trial_idx, n_trials, rng, db_best)
            score = self._evaluate_direction_accuracy(X, y, params)

            self.history.append({
                "trial": trial_idx,
                "direction_accuracy": round(score * 100, 1),
                "params": params.copy(),
            })

            if score > best_score:
                best_score = score
                best_params = params.copy()

        self.best_params = best_params
        self.best_score = best_score

        # --- 結果をDBに保存 ---
        if best_params:
            self.db.save_model_params(
                self.ticker, "xgboost", best_params,
                performance_mae=None)
            self.db.save_backtest_result(
                ticker=self.ticker,
                horizon=self.horizon,
                train_ratio=0.0,
                direction_accuracy=best_score * 100,
                sharpe_ratio=0.0,
                win_rate=best_score * 100,
                total_return=0.0,
                profit_factor=0.0,
                xgb_params=best_params,
                prophet_params=None,
                weights=None,
                source="auto_ml",
            )

        return {
            "best_params": best_params,
            "best_direction_accuracy": round(best_score * 100, 1),
            "trials": n_trials,
            "history": self.history,
        }

    def _sample_params(self, trial_idx, total, rng, db_best=None):
        """プリセット → DB最良の変異 → ランダム探索"""
        # Phase 1: プリセット
        if trial_idx < len(PRESETS):
            params = PRESETS[trial_idx].copy()
        # Phase 2: DB最良パラメータの近傍探索
        elif db_best and trial_idx < len(PRESETS) + 5:
            params = self._mutate_params(db_best, rng)
        # Phase 3: 現在ベストの近傍探索（発見済みなら）
        elif self.best_params and rng.random() < 0.4:
            params = self._mutate_params(self.best_params, rng)
        # Phase 4: 完全ランダム
        else:
            params = {k: rng.choice(v) for k, v in SEARCH_SPACE.items()}

        params["objective"] = "reg:squarederror"
        params["random_state"] = 42
        return params

    def _mutate_params(self, base, rng):
        """ベースパラメータの1-3個をランダムに変異"""
        params = base.copy()
        keys_to_mutate = rng.sample(list(SEARCH_SPACE.keys()),
                                     k=rng.randint(1, 3))
        for key in keys_to_mutate:
            params[key] = rng.choice(SEARCH_SPACE[key])
        return params

    def _evaluate_direction_accuracy(self, X, y, params):
        """TimeSeriesSplit CVで方向精度を評価"""
        n_splits = min(5, max(2, len(X) // 80))
        tscv = TimeSeriesSplit(n_splits=n_splits)
        scores = []

        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            try:
                fit_params = params.copy()
                n_est = fit_params.pop("n_estimators", 500)
                # 安全にXGBRegressor固有でないパラメータを除外
                for k in list(fit_params.keys()):
                    if k not in ("max_depth", "learning_rate", "subsample",
                                 "colsample_bytree", "reg_alpha", "reg_lambda",
                                 "min_child_weight", "gamma", "objective",
                                 "random_state"):
                        fit_params.pop(k)

                model = XGBRegressor(
                    n_estimators=n_est,
                    early_stopping_rounds=20,
                    **fit_params)
                model.fit(X_train, y_train,
                          eval_set=[(X_val, y_val)], verbose=False)
                pred = model.predict(X_val)

                # 方向正解率
                correct = sum(
                    1 for p, a in zip(pred, y_val.values)
                    if (p > 0) == (a > 0))
                scores.append(correct / len(y_val) if len(y_val) > 0 else 0.5)
            except Exception:
                scores.append(0.5)

        return float(np.mean(scores)) if scores else 0.5
