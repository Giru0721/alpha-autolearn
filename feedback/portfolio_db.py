"""ポートフォリオ管理データベース"""

import sqlite3
from contextlib import contextmanager

import pandas as pd

from config import DATABASE_PATH


class PortfolioDB:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_tables()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
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
                CREATE TABLE IF NOT EXISTS portfolio (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_email  TEXT NOT NULL,
                    ticker      TEXT NOT NULL,
                    shares      REAL NOT NULL DEFAULT 0,
                    avg_price   REAL NOT NULL DEFAULT 0,
                    memo        TEXT DEFAULT '',
                    added_at    TEXT DEFAULT (datetime('now')),
                    updated_at  TEXT DEFAULT (datetime('now')),
                    UNIQUE(user_email, ticker)
                );
                CREATE INDEX IF NOT EXISTS idx_portfolio_user ON portfolio(user_email);

                CREATE TABLE IF NOT EXISTS watchlist (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_email  TEXT NOT NULL,
                    ticker      TEXT NOT NULL,
                    added_at    TEXT DEFAULT (datetime('now')),
                    UNIQUE(user_email, ticker)
                );
                CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist(user_email);

                CREATE TABLE IF NOT EXISTS price_alerts (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_email  TEXT NOT NULL,
                    ticker      TEXT NOT NULL,
                    condition   TEXT NOT NULL,
                    target_price REAL NOT NULL,
                    triggered   INTEGER DEFAULT 0,
                    created_at  TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_alerts_user ON price_alerts(user_email);
            """)

    def add_holding(self, user_email: str, ticker: str, shares: float,
                    price: float, memo: str = "") -> bool:
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT shares, avg_price FROM portfolio WHERE user_email=? AND ticker=?",
                (user_email.lower(), ticker)).fetchone()
            if existing:
                old_shares = existing["shares"]
                old_avg = existing["avg_price"]
                new_shares = old_shares + shares
                if new_shares > 0:
                    new_avg = (old_shares * old_avg + shares * price) / new_shares
                else:
                    new_avg = 0
                conn.execute("""
                    UPDATE portfolio SET shares=?, avg_price=?, memo=?,
                    updated_at=datetime('now') WHERE user_email=? AND ticker=?
                """, (new_shares, new_avg, memo, user_email.lower(), ticker))
            else:
                conn.execute("""
                    INSERT INTO portfolio (user_email, ticker, shares, avg_price, memo)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_email.lower(), ticker, shares, price, memo))
            return True

    def remove_holding(self, user_email: str, ticker: str):
        with self._connect() as conn:
            conn.execute("DELETE FROM portfolio WHERE user_email=? AND ticker=?",
                         (user_email.lower(), ticker))

    def get_holdings(self, user_email: str) -> pd.DataFrame:
        with self._connect() as conn:
            return pd.read_sql_query(
                "SELECT * FROM portfolio WHERE user_email=? AND shares > 0 ORDER BY updated_at DESC",
                conn, params=(user_email.lower(),))

    def add_to_watchlist(self, user_email: str, ticker: str) -> bool:
        with self._connect() as conn:
            try:
                conn.execute("INSERT INTO watchlist (user_email, ticker) VALUES (?, ?)",
                             (user_email.lower(), ticker))
                return True
            except sqlite3.IntegrityError:
                return False

    def remove_from_watchlist(self, user_email: str, ticker: str):
        with self._connect() as conn:
            conn.execute("DELETE FROM watchlist WHERE user_email=? AND ticker=?",
                         (user_email.lower(), ticker))

    def get_watchlist(self, user_email: str) -> list:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ticker FROM watchlist WHERE user_email=? ORDER BY added_at DESC",
                (user_email.lower(),)).fetchall()
            return [r["ticker"] for r in rows]

    def add_price_alert(self, user_email: str, ticker: str,
                        condition: str, target_price: float):
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO price_alerts (user_email, ticker, condition, target_price)
                VALUES (?, ?, ?, ?)
            """, (user_email.lower(), ticker, condition, target_price))

    def get_active_alerts(self, user_email: str) -> pd.DataFrame:
        with self._connect() as conn:
            return pd.read_sql_query(
                "SELECT * FROM price_alerts WHERE user_email=? AND triggered=0 ORDER BY created_at DESC",
                conn, params=(user_email.lower(),))

    def trigger_alert(self, alert_id: int):
        with self._connect() as conn:
            conn.execute("UPDATE price_alerts SET triggered=1 WHERE id=?", (alert_id,))

    def delete_alert(self, alert_id: int):
        with self._connect() as conn:
            conn.execute("DELETE FROM price_alerts WHERE id=?", (alert_id,))
