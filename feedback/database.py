"""SQLiteデータベース管理 - 予測履歴・モデルパラメータ・誤差追跡"""

import json
import sqlite3
from contextlib import contextmanager

import pandas as pd

from config import DATABASE_PATH, ENSEMBLE_INITIAL_WEIGHTS


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_tables()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_tables(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker          TEXT NOT NULL,
                    prediction_date TEXT NOT NULL,
                    target_date     TEXT NOT NULL,
                    horizon_days    INTEGER NOT NULL,
                    current_price   REAL NOT NULL,
                    predicted_price REAL NOT NULL,
                    predicted_return REAL NOT NULL,
                    prophet_pred    REAL,
                    xgboost_pred    REAL,
                    actual_price    REAL,
                    actual_return   REAL,
                    error           REAL,
                    abs_error       REAL,
                    direction_correct INTEGER,
                    confidence_lower REAL,
                    confidence_upper REAL,
                    created_at      TEXT DEFAULT (datetime('now')),
                    UNIQUE(ticker, prediction_date, horizon_days)
                );
                CREATE INDEX IF NOT EXISTS idx_pred_ticker ON predictions(ticker);
                CREATE INDEX IF NOT EXISTS idx_pred_target ON predictions(ticker, target_date);

                CREATE TABLE IF NOT EXISTS model_weights (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker          TEXT NOT NULL,
                    prophet_weight  REAL NOT NULL,
                    xgboost_weight  REAL NOT NULL,
                    mae_prophet     REAL,
                    mae_xgboost     REAL,
                    reason          TEXT,
                    created_at      TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_weights_ticker ON model_weights(ticker);

                CREATE TABLE IF NOT EXISTS model_params (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker          TEXT NOT NULL,
                    model_name      TEXT NOT NULL,
                    params_json     TEXT NOT NULL,
                    performance_mae REAL,
                    created_at      TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_params_ticker ON model_params(ticker, model_name);

                CREATE TABLE IF NOT EXISTS error_snapshots (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker          TEXT NOT NULL,
                    snapshot_date   TEXT NOT NULL,
                    horizon_days    INTEGER NOT NULL,
                    mae             REAL,
                    rmse            REAL,
                    mape            REAL,
                    directional_accuracy REAL,
                    total_predictions INTEGER,
                    prophet_mae     REAL,
                    xgboost_mae     REAL,
                    ensemble_mae    REAL,
                    created_at      TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS stock_votes (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    email       TEXT NOT NULL,
                    ticker      TEXT NOT NULL,
                    vote_date   TEXT NOT NULL,
                    direction   TEXT NOT NULL CHECK(direction IN ('up', 'down')),
                    created_at  TEXT DEFAULT (datetime('now')),
                    UNIQUE(email, ticker, vote_date)
                );
                CREATE INDEX IF NOT EXISTS idx_votes_ticker_date
                    ON stock_votes(ticker, vote_date);
            """)

    # ===== 投票機能 =====
    def cast_vote(self, email: str, ticker: str, direction: str) -> bool:
        """投票を記録（1日1銘柄1票）。成功でTrue。"""
        with self._connect() as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO stock_votes (email, ticker, vote_date, direction)
                    VALUES (?, ?, date('now'), ?)
                """, (email.lower(), ticker, direction))
                return True
            except Exception:
                return False

    def get_vote_summary(self, ticker: str) -> dict:
        """本日の投票結果を取得"""
        with self._connect() as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN direction='up' THEN 1 ELSE 0 END) as up_count,
                    SUM(CASE WHEN direction='down' THEN 1 ELSE 0 END) as down_count
                FROM stock_votes
                WHERE ticker=? AND vote_date=date('now')
            """, (ticker,)).fetchone()
            total = row["total"] or 0
            up = row["up_count"] or 0
            down = row["down_count"] or 0
            return {
                "total": total,
                "up": up,
                "down": down,
                "up_pct": round(up / total * 100, 1) if total > 0 else 50.0,
                "down_pct": round(down / total * 100, 1) if total > 0 else 50.0,
            }

    def get_user_vote(self, email: str, ticker: str) -> str | None:
        """ユーザーの本日の投票を取得"""
        with self._connect() as conn:
            row = conn.execute("""
                SELECT direction FROM stock_votes
                WHERE email=? AND ticker=? AND vote_date=date('now')
            """, (email.lower(), ticker)).fetchone()
            return row["direction"] if row else None

    def save_prediction(self, ticker, prediction_date, target_date,
                        horizon_days, current_price, predicted_price,
                        predicted_return, prophet_pred, xgboost_pred,
                        confidence_lower, confidence_upper):
        with self._connect() as conn:
            cur = conn.execute("""
                INSERT OR REPLACE INTO predictions
                (ticker, prediction_date, target_date, horizon_days,
                 current_price, predicted_price, predicted_return,
                 prophet_pred, xgboost_pred, confidence_lower, confidence_upper)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ticker, prediction_date, target_date, horizon_days,
                  current_price, predicted_price, predicted_return,
                  prophet_pred, xgboost_pred, confidence_lower, confidence_upper))
            return cur.lastrowid

    def update_actual(self, prediction_id, actual_price, actual_return,
                      error, direction_correct):
        with self._connect() as conn:
            conn.execute("""
                UPDATE predictions
                SET actual_price=?, actual_return=?, error=?,
                    abs_error=ABS(?), direction_correct=?
                WHERE id=?
            """, (actual_price, actual_return, error, error,
                  direction_correct, prediction_id))

    def get_unresolved_predictions(self, ticker):
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT * FROM predictions
                WHERE ticker=? AND actual_price IS NULL
                  AND target_date <= date('now')
                ORDER BY target_date
            """, (ticker,)).fetchall()
            return [dict(r) for r in rows]

    def get_resolved_predictions(self, ticker, limit=100):
        with self._connect() as conn:
            return pd.read_sql_query("""
                SELECT * FROM predictions
                WHERE ticker=? AND actual_price IS NOT NULL
                ORDER BY prediction_date DESC LIMIT ?
            """, conn, params=(ticker, limit))

    def get_all_predictions(self, ticker):
        with self._connect() as conn:
            return pd.read_sql_query(
                "SELECT * FROM predictions WHERE ticker=? ORDER BY prediction_date DESC",
                conn, params=(ticker,))

    def save_weights(self, ticker, prophet_weight, xgboost_weight,
                     mae_prophet=None, mae_xgboost=None, reason=""):
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO model_weights
                (ticker, prophet_weight, xgboost_weight, mae_prophet, mae_xgboost, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ticker, prophet_weight, xgboost_weight,
                  mae_prophet, mae_xgboost, reason))

    def load_weights(self, ticker):
        with self._connect() as conn:
            row = conn.execute("""
                SELECT prophet_weight, xgboost_weight FROM model_weights
                WHERE ticker=? ORDER BY created_at DESC LIMIT 1
            """, (ticker,)).fetchone()
            if row:
                return {"prophet": row["prophet_weight"],
                        "xgboost": row["xgboost_weight"]}
            return ENSEMBLE_INITIAL_WEIGHTS.copy()

    def get_weight_history(self, ticker):
        with self._connect() as conn:
            return pd.read_sql_query(
                "SELECT * FROM model_weights WHERE ticker=? ORDER BY created_at",
                conn, params=(ticker,))

    def save_model_params(self, ticker, model_name, params, performance_mae=None):
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO model_params (ticker, model_name, params_json, performance_mae)
                VALUES (?, ?, ?, ?)
            """, (ticker, model_name, json.dumps(params), performance_mae))

    def load_model_params(self, ticker, model_name):
        with self._connect() as conn:
            row = conn.execute("""
                SELECT params_json FROM model_params
                WHERE ticker=? AND model_name=?
                ORDER BY created_at DESC LIMIT 1
            """, (ticker, model_name)).fetchone()
            if row:
                return json.loads(row["params_json"])
            return None

    def save_error_snapshot(self, ticker, horizon_days, mae, rmse, mape,
                            directional_accuracy, total_predictions,
                            prophet_mae, xgboost_mae, ensemble_mae):
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO error_snapshots
                (ticker, snapshot_date, horizon_days, mae, rmse, mape,
                 directional_accuracy, total_predictions,
                 prophet_mae, xgboost_mae, ensemble_mae)
                VALUES (?, date('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ticker, horizon_days, mae, rmse, mape,
                  directional_accuracy, total_predictions,
                  prophet_mae, xgboost_mae, ensemble_mae))

    def get_error_history(self, ticker):
        with self._connect() as conn:
            return pd.read_sql_query(
                "SELECT * FROM error_snapshots WHERE ticker=? ORDER BY snapshot_date",
                conn, params=(ticker,))
