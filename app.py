"""Alpha-AutoLearn - AI株価予測システム メインエントリーポイント"""

import sys
import os
import hashlib

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(__file__))

# SSL証明書パス修正 (日本語フォルダ名でcurl_cffiが失敗する問題の対策)
_cert_home = os.path.join(os.path.expanduser("~"), "cacert.pem")
if not os.path.exists(_cert_home):
    try:
        import certifi, shutil
        shutil.copy2(certifi.where(), _cert_home)
    except Exception:
        pass
if os.path.exists(_cert_home):
    os.environ.setdefault("CURL_CA_BUNDLE", _cert_home)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _cert_home)

import streamlit as st
from PIL import Image
from ui.styles import CUSTOM_CSS, VIEWPORT_META
from ui.layout import render_sidebar, render_main_content
from ui.auth_ui import render_auth_page, render_user_badge, render_subscription_page, get_auth_manager
from ui.i18n import TEXTS
from feedback.database import Database

_ICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
_SESSION_SECRET = "alpha-autolearn-2024"


def _make_token(email: str) -> str:
    return hashlib.sha256((_SESSION_SECRET + email).encode()).hexdigest()[:16]


def _try_restore_session():
    """クエリパラメータからセッション復元"""
    if "user_email" in st.session_state:
        return
    params = st.query_params
    token = params.get("t", "")
    email = params.get("u", "")
    if email and token and _make_token(email) == token:
        auth = get_auth_manager()
        user = auth.get_user(email)
        if user:
            st.session_state["user_email"] = email
            st.session_state["user"] = user


def _save_session_to_params(email: str):
    """ログイン後にクエリパラメータにセッション保存"""
    st.query_params["u"] = email
    st.query_params["t"] = _make_token(email)


def _handle_checkout_return():
    """Stripe決済完了後 → プラン即時反映"""
    session_id = st.query_params.get("session_id", "")
    if not session_id:
        return
    # 二重処理防止
    if st.session_state.get("_checkout_verified") == session_id:
        return

    auth = get_auth_manager()
    upgraded = False

    # 方法1: Stripe API で検証（最も安全）
    result = auth.verify_checkout_session(session_id)
    if result:
        upgraded = True
        email = result["email"]
    else:
        # 方法2: URLパラメータから即時反映
        # Stripeは決済成功時のみ success_url にリダイレクトするので信頼可能
        plan_key = st.query_params.get("plan", "")
        pay_token = st.query_params.get("pt", "")
        email = st.query_params.get("u", "")
        if email and plan_key and pay_token:
            expected = hashlib.sha256(
                f"{email}:{plan_key}:alpha-pay".encode()).hexdigest()[:12]
            if pay_token == expected:
                from datetime import datetime, timedelta
                expires = (datetime.now() + timedelta(days=31)).isoformat()
                auth._update_plan(email, plan_key, expires_at=expires)
                upgraded = True

    if upgraded:
        st.session_state["_checkout_verified"] = session_id
        user = auth.get_user(email)
        if user:
            st.session_state["user_email"] = email
            st.session_state["user"] = user
        st.session_state["_checkout_success"] = True

    # 決済関連パラメータを除去（u, t は保持）
    for key in ["session_id", "plan", "pt"]:
        try:
            del st.query_params[key]
        except Exception:
            pass


def main():
    _icon = Image.open(_ICON_PATH) if os.path.exists(_ICON_PATH) else TEXTS["app_icon"]
    st.set_page_config(
        page_title=TEXTS["app_title"],
        page_icon=_icon,
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(VIEWPORT_META, unsafe_allow_html=True)
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    if "db" not in st.session_state:
        st.session_state["db"] = Database()

    # セッション復元
    _try_restore_session()

    # Stripe決済完了後のプラン反映
    _handle_checkout_return()

    # 決済成功メッセージ
    if st.session_state.pop("_checkout_success", False):
        st.toast("決済が完了しました！プランがアップグレードされました 🎉")

    # 認証チェック
    if "user_email" not in st.session_state:
        render_auth_page()
        return

    # ログイン済み → クエリパラメータにセッション保存
    _save_session_to_params(st.session_state["user_email"])

    # メインアプリ
    settings = render_sidebar()

    # ルーティング
    if settings.get("show_admin"):
        from ui.admin import render_admin_page
        render_admin_page()
    elif settings.get("show_subscription"):
        render_subscription_page()
    else:
        st.session_state["page"] = "main"
        render_main_content(settings)


if __name__ == "__main__":
    main()
