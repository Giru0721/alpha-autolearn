"""サブスクリプション管理 - Stripe連携 + ローカル認証"""

import os
import hashlib
import sqlite3
import secrets
from datetime import datetime, timedelta
from contextlib import contextmanager

import stripe

from config import DATABASE_PATH, ADMIN_EMAIL as _ADMIN_EMAIL, ADMIN_PASSWORD as _ADMIN_PASSWORD


def _get_admin_creds():
    """管理者情報を環境変数 → Streamlit Secrets から取得"""
    email = _ADMIN_EMAIL
    password = _ADMIN_PASSWORD
    if not email:
        try:
            import streamlit as st
            email = st.secrets.get("ADMIN_EMAIL", "") or st.secrets["ADMIN_EMAIL"]
        except Exception:
            pass
    if not password:
        try:
            import streamlit as st
            password = st.secrets.get("ADMIN_PASSWORD", "") or st.secrets["ADMIN_PASSWORD"]
        except Exception:
            pass
    return email, password

# Stripe設定（環境変数から取得）
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# プラン定義
PLANS = {
    "free": {
        "name": "無料プラン", "name_en": "Free",
        "price": 0, "predictions_per_day": 3, "horizons_max": 30,
        "features": ["基本テクニカル指標", "価格チャート", "5日後まで予測"],
        "features_en": ["Basic indicators", "Price chart", "5-day forecast"],
        "stripe_price_id": None,
    },
    "pro": {
        "name": "プロプラン", "name_en": "Pro",
        "price": 980, "predictions_per_day": 30, "horizons_max": 365,
        "features": ["全テクニカル指標", "FRED経済データ", "1年予測", "シナリオ分析", "自動調整", "ポートフォリオ管理"],
        "features_en": ["All indicators", "FRED data", "1-year forecast", "Scenarios", "Auto-adjust", "Portfolio"],
        "stripe_price_id": os.environ.get("STRIPE_PRO_PRICE_ID", ""),
    },
    "premium": {
        "name": "プレミアムプラン", "name_en": "Premium",
        "price": 2980, "predictions_per_day": -1, "horizons_max": 365,
        "features": ["全プロ機能", "ニュースセンチメント", "Googleトレンド", "バックテスト", "API連携", "優先サポート"],
        "features_en": ["All Pro features", "News sentiment", "Google Trends", "Backtesting", "API", "Priority support"],
        "stripe_price_id": os.environ.get("STRIPE_PREMIUM_PRICE_ID", ""),
    },
    "admin": {
        "name": "管理者", "name_en": "Admin",
        "price": 0, "predictions_per_day": -1, "horizons_max": 365,
        "features": ["全機能無制限", "管理者パネル", "ユーザー管理"],
        "features_en": ["Unlimited access", "Admin panel", "User management"],
        "stripe_price_id": None,
    },
}


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()


class AuthManager:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_auth_tables()
        self._ensure_admin()

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

    def _init_auth_tables(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    email           TEXT NOT NULL UNIQUE,
                    password_hash   TEXT NOT NULL,
                    salt            TEXT NOT NULL,
                    display_name    TEXT,
                    role            TEXT DEFAULT 'user',
                    plan            TEXT DEFAULT 'free',
                    stripe_customer_id TEXT,
                    stripe_subscription_id TEXT,
                    plan_expires_at TEXT,
                    predictions_today INTEGER DEFAULT 0,
                    predictions_date TEXT,
                    created_at      TEXT DEFAULT (datetime('now')),
                    updated_at      TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_users_stripe ON users(stripe_customer_id);
            """)
            # role列の追加（既存DBの互換性）
            try:
                conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            except sqlite3.OperationalError:
                pass  # 既に存在する場合

    def _ensure_admin(self):
        """管理者アカウントの自動作成・パスワード同期"""
        admin_email, admin_password = _get_admin_creds()
        if not admin_email or not admin_password:
            return
        user = self.get_user(admin_email)
        if not user:
            self.register(admin_email, admin_password, "管理者")
            with self._connect() as conn:
                conn.execute("UPDATE users SET role='admin', plan='admin' WHERE email=?",
                             (admin_email.lower(),))
        else:
            salt = secrets.token_hex(16)
            pw_hash = _hash_password(admin_password, salt)
            with self._connect() as conn:
                conn.execute(
                    "UPDATE users SET role='admin', plan='admin', "
                    "password_hash=?, salt=? WHERE email=?",
                    (pw_hash, salt, admin_email.lower()))

    def register(self, email: str, password: str, display_name: str = "") -> dict:
        salt = secrets.token_hex(16)
        pw_hash = _hash_password(password, salt)
        with self._connect() as conn:
            try:
                _ae, _ = _get_admin_creds()
                role = "admin" if (_ae and email.lower().strip() == _ae.lower()) else "user"
                plan = "admin" if role == "admin" else "free"
                conn.execute("""
                    INSERT INTO users (email, password_hash, salt, display_name, role, plan)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (email.lower().strip(), pw_hash, salt,
                      display_name or email.split("@")[0], role, plan))
                return {"success": True, "message": "登録完了"}
            except sqlite3.IntegrityError:
                return {"success": False, "message": "このメールアドレスは既に登録されています"}

    def login(self, email: str, password: str) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email=?", (email.lower().strip(),)
            ).fetchone()
            if not row:
                return {"success": False, "message": "メールアドレスまたはパスワードが正しくありません"}
            if _hash_password(password, row["salt"]) != row["password_hash"]:
                return {"success": False, "message": "メールアドレスまたはパスワードが正しくありません"}
            return {"success": True, "user": dict(row)}

    def get_user(self, email: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE email=?", (email.lower(),)).fetchone()
            return dict(row) if row else None

    def get_plan(self, email: str) -> dict:
        user = self.get_user(email)
        if not user:
            return PLANS["free"]
        if user.get("role") == "admin":
            return PLANS["admin"]
        plan_key = user.get("plan", "free")
        expires = user.get("plan_expires_at")
        if plan_key != "free" and expires:
            if datetime.fromisoformat(expires) < datetime.now():
                self._update_plan(email, "free")
                return PLANS["free"]
        return PLANS.get(plan_key, PLANS["free"])

    def check_prediction_limit(self, email: str, bonus_available: int = 0) -> dict:
        """予測回数制限チェック（ボーナス考慮）"""
        user = self.get_user(email)
        if not user:
            return {"allowed": False, "remaining": 0, "message": "ログインが必要です",
                    "use_bonus": False}
        if user.get("role") == "admin":
            return {"allowed": True, "remaining": -1, "message": "管理者: 無制限",
                    "use_bonus": False}
        plan = self.get_plan(email)
        limit = plan["predictions_per_day"]
        if limit == -1:
            return {"allowed": True, "remaining": -1, "message": "無制限",
                    "use_bonus": False}
        today = datetime.now().strftime("%Y-%m-%d")
        count = user["predictions_today"] if user["predictions_date"] == today else 0
        if count < limit:
            return {"allowed": True, "remaining": limit - count, "message": "OK",
                    "use_bonus": False}
        # 上限到達 → ボーナスがあれば使用許可
        if bonus_available > 0:
            return {"allowed": True, "remaining": 0,
                    "message": "投票ボーナスを使用します",
                    "use_bonus": True}
        return {"allowed": False, "remaining": 0,
                "message": f"本日の予測上限({limit}回)に達しました。投票で的中するとボーナス予測が獲得できます！",
                "use_bonus": False}

    def increment_prediction_count(self, email: str):
        today = datetime.now().strftime("%Y-%m-%d")
        with self._connect() as conn:
            user = conn.execute("SELECT predictions_date, predictions_today FROM users WHERE email=?",
                                (email.lower(),)).fetchone()
            if user and user["predictions_date"] == today:
                conn.execute("UPDATE users SET predictions_today = predictions_today + 1 WHERE email=?",
                             (email.lower(),))
            else:
                conn.execute("UPDATE users SET predictions_today = 1, predictions_date = ? WHERE email=?",
                             (today, email.lower()))

    def _update_plan(self, email: str, plan: str, expires_at: str = None,
                     stripe_sub_id: str = None):
        with self._connect() as conn:
            conn.execute("""
                UPDATE users SET plan=?, plan_expires_at=?, stripe_subscription_id=?,
                updated_at=datetime('now') WHERE email=?
            """, (plan, expires_at, stripe_sub_id, email.lower()))

    def get_all_users(self) -> list:
        """全ユーザー一覧（管理者用）"""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, email, display_name, role, plan, predictions_today, "
                "predictions_date, created_at FROM users ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def update_user_plan(self, email: str, plan: str):
        """管理者によるプラン変更"""
        self._update_plan(email, plan, expires_at="2099-12-31T23:59:59")

    def delete_user(self, email: str):
        """ユーザー削除（管理者用）"""
        with self._connect() as conn:
            conn.execute("DELETE FROM users WHERE email=? AND role != 'admin'",
                         (email.lower(),))

    def _get_stripe_key(self) -> str:
        """Stripe APIキーを実行時に取得（環境変数 + Streamlit Secrets）"""
        api_key = os.environ.get("STRIPE_SECRET_KEY", "")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets["STRIPE_SECRET_KEY"]
            except Exception:
                pass
        return api_key or ""

    def create_checkout_session(self, email: str, plan_key: str, success_url: str,
                                cancel_url: str) -> str | None:
        """Stripe Checkout セッション作成（単発決済 - PayPay/コンビニ対応）"""
        api_key = self._get_stripe_key()
        if not api_key:
            return None
        stripe.api_key = api_key

        plan = PLANS.get(plan_key)
        if not plan or plan["price"] == 0:
            return None
        user = self.get_user(email)
        if not user:
            return None
        # Stripeカスタマー作成/取得
        customer_id = user.get("stripe_customer_id")
        if not customer_id:
            customer = stripe.Customer.create(email=email)
            customer_id = customer.id
            with self._connect() as conn:
                conn.execute("UPDATE users SET stripe_customer_id=? WHERE email=?",
                             (customer_id, email.lower()))
        # success_url に session_id + plan 情報を付与
        separator = "&" if "?" in success_url else "?"
        # 決済成功トークン生成（URL改竄防止）
        import hashlib as _hl
        pay_token = _hl.sha256(f"{email}:{plan_key}:alpha-pay".encode()).hexdigest()[:12]
        full_success = (success_url + separator +
                        f"session_id={{CHECKOUT_SESSION_ID}}&plan={plan_key}&pt={pay_token}")
        session_params = dict(
            customer=customer_id,
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "jpy",
                    "product_data": {
                        "name": f"Alpha-AutoLearn {plan.get('name_en', plan['name'])}（1ヶ月）",
                    },
                    "unit_amount": plan["price"],
                },
                "quantity": 1,
            }],
            success_url=full_success,
            cancel_url=cancel_url,
            metadata={"email": email, "plan": plan_key},
            allow_promotion_codes=True,
            locale="ja",
        )
        try:
            # payment_method_types 未指定 → Stripeダッシュボードで有効化済みの
            # 全決済手段（Card, PayPay, コンビニ等）が自動で表示される
            session = stripe.checkout.Session.create(**session_params)
        except Exception:
            # フォールバック: カードのみ
            session_params["payment_method_types"] = ["card"]
            session = stripe.checkout.Session.create(**session_params)
        return session.url

    def verify_checkout_session(self, session_id: str) -> dict | None:
        """Stripe決済完了を検証してプラン反映"""
        api_key = self._get_stripe_key()
        if not api_key:
            return None
        stripe.api_key = api_key
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                email = (session.metadata or {}).get("email", "")
                plan_key = (session.metadata or {}).get("plan", "")
                if email and plan_key:
                    expires = (datetime.now() + timedelta(days=31)).isoformat()
                    self._update_plan(email, plan_key, expires_at=expires)
                    return {"email": email, "plan": plan_key}
            return None
        except Exception as e:
            print(f"[Stripe verify error] session_id={session_id} error={e}")
            return None

    def sync_plan_from_stripe(self, email: str) -> str | None:
        """Stripeの決済履歴からプランを同期（過去の決済も反映）"""
        api_key = self._get_stripe_key()
        if not api_key:
            return None
        stripe.api_key = api_key
        user = self.get_user(email)
        if not user:
            return None
        customer_id = user.get("stripe_customer_id")
        if not customer_id:
            return None
        try:
            sessions = stripe.checkout.Session.list(
                customer=customer_id,
                status="complete",
                limit=10,
            )
            for s in sessions.data:
                if s.payment_status == "paid":
                    plan_key = (s.metadata or {}).get("plan", "")
                    if plan_key and plan_key in PLANS:
                        expires = (datetime.now() + timedelta(days=31)).isoformat()
                        self._update_plan(email, plan_key, expires_at=expires)
                        return plan_key
        except Exception as e:
            print(f"[Stripe sync error] {e}")
        return None

    def handle_webhook(self, payload: bytes, sig_header: str) -> bool:
        """Stripe Webhook処理"""
        if not STRIPE_WEBHOOK_SECRET:
            return False
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except Exception:
            return False
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            email = session["metadata"]["email"]
            plan_key = session["metadata"]["plan"]
            expires = (datetime.now() + timedelta(days=31)).isoformat()
            self._update_plan(email, plan_key, expires)
        elif event["type"] == "customer.subscription.deleted":
            sub = event["data"]["object"]
            customer_id = sub["customer"]
            with self._connect() as conn:
                conn.execute("""
                    UPDATE users SET plan='free', stripe_subscription_id=NULL,
                    plan_expires_at=NULL WHERE stripe_customer_id=?
                """, (customer_id,))
        return True
