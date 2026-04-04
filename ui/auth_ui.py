"""認証・サブスクリプションUI"""

import streamlit as st
from auth.subscription import AuthManager, PLANS
from ui.i18n import T, get_lang, set_lang


def get_auth_manager():
    if "auth_manager" not in st.session_state:
        st.session_state["auth_manager"] = AuthManager()
    return st.session_state["auth_manager"]


def render_language_selector():
    """言語切替セレクタ"""
    lang = get_lang()
    cols = st.columns([1, 1])
    with cols[0]:
        if st.button("🇯🇵 日本語", use_container_width=True,
                     disabled=(lang == "ja"), key="lang_ja"):
            set_lang("ja")
            st.rerun()
    with cols[1]:
        if st.button("🇺🇸 English", use_container_width=True,
                     disabled=(lang == "en"), key="lang_en"):
            set_lang("en")
            st.rerun()


def render_auth_page():
    """ログイン/新規登録ページ"""
    render_language_selector()
    st.markdown("### 🔐 " + ("ログイン / 新規登録" if get_lang() == "ja" else "Login / Register"))
    tab_login, tab_register = st.tabs(
        ["ログイン" if get_lang() == "ja" else "Login",
         "新規登録" if get_lang() == "ja" else "Register"])

    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pw")
        if st.button("Login" if get_lang() == "en" else "ログイン",
                     type="primary", use_container_width=True, key="login_btn"):
            if not email or not password:
                st.error("Enter email and password")
                return
            auth = get_auth_manager()
            result = auth.login(email, password)
            if result["success"]:
                st.session_state["user_email"] = email.lower().strip()
                st.session_state["user"] = result["user"]
                st.rerun()
            else:
                st.error(result["message"])

    with tab_register:
        new_email = st.text_input("Email", key="reg_email")
        new_name = st.text_input("Display Name" if get_lang() == "en" else "表示名（任意）",
                                 key="reg_name")
        new_pw = st.text_input("Password (8+)" if get_lang() == "en" else "パスワード（8文字以上）",
                               type="password", key="reg_pw")
        new_pw2 = st.text_input("Confirm" if get_lang() == "en" else "パスワード確認",
                                type="password", key="reg_pw2")
        if st.button("Register" if get_lang() == "en" else "無料で登録",
                     type="primary", use_container_width=True, key="reg_btn"):
            if not new_email or not new_pw:
                st.error("Enter email and password")
                return
            if len(new_pw) < 8:
                st.error("Password must be 8+ characters" if get_lang() == "en"
                         else "パスワードは8文字以上にしてください")
                return
            if new_pw != new_pw2:
                st.error("Passwords don't match" if get_lang() == "en"
                         else "パスワードが一致しません")
                return
            auth = get_auth_manager()
            result = auth.register(new_email, new_pw, new_name)
            if result["success"]:
                st.success("Registered! Please login." if get_lang() == "en"
                           else "登録完了！ログインしてください。")
            else:
                st.error(result["message"])

    st.divider()
    if st.button("Continue as Guest" if get_lang() == "en" else "ゲストとして続ける（制限あり）",
                 use_container_width=True, key="guest_btn"):
        st.session_state["user_email"] = "guest"
        st.session_state["user"] = {"plan": "free", "display_name": "Guest", "email": "guest"}
        st.rerun()


def render_subscription_page():
    """サブスクリプション管理ページ"""
    email = st.session_state.get("user_email", "")
    auth = get_auth_manager()
    current_plan = auth.get_plan(email) if email and email != "guest" else PLANS["free"]
    current_key = "free"
    for k, v in PLANS.items():
        if v["name"] == current_plan["name"]:
            current_key = k
            break

    lang = get_lang()
    st.markdown("### " + (T("admin_panel") if False else "Plan" if lang == "en" else "プラン選択"))
    display_plans = {k: v for k, v in PLANS.items() if k != "admin"}
    cols = st.columns(len(display_plans))

    for col, (key, plan) in zip(cols, display_plans.items()):
        with col:
            is_current = (key == current_key)
            border = "2px solid #4da6ff" if is_current else "1px solid #30363d"
            badge = ("Current" if lang == "en" else "現在のプラン") if is_current else ""
            plan_name = plan.get("name_en", plan["name"]) if lang == "en" else plan["name"]
            price_text = ("Free" if lang == "en" else "無料") if plan["price"] == 0 else f"¥{plan['price']:,}/mo"
            limit_text = ("Unlimited" if lang == "en" else "無制限") if plan["predictions_per_day"] == -1 else f"{plan['predictions_per_day']}/day"
            features = plan.get("features_en", plan["features"]) if lang == "en" else plan["features"]
            features_html = "".join(f"<li>{f}</li>" for f in features)

            st.markdown(f"""
            <div style="background:#161b22; border-radius:12px; padding:20px; border:{border};
                        text-align:center; min-height:380px;">
                <div style="font-size:0.8em; color:#4da6ff; min-height:20px;">{badge}</div>
                <h3 style="margin:8px 0;">{plan_name}</h3>
                <div style="font-size:1.8em; font-weight:bold; color:#4da6ff; margin:12px 0;">
                    {price_text}
                </div>
                <div style="color:#8b949e; margin-bottom:12px;">{limit_text}</div>
                <ul style="text-align:left; color:#c9d1d9; font-size:0.85em; padding-left:20px;">
                    {features_html}
                </ul>
            </div>
            """, unsafe_allow_html=True)

            if not is_current and key != "free" and email and email != "guest":
                if st.button(f"Upgrade to {plan_name}" if lang == "en" else f"{plan_name}にアップグレード",
                             key=f"upgrade_{key}", use_container_width=True):
                    app_url = st.session_state.get("app_url", "http://localhost:8501")
                    checkout_url = auth.create_checkout_session(email, key, app_url, app_url)
                    if checkout_url:
                        st.markdown(f'<a href="{checkout_url}" target="_blank">'
                                    f'<button style="width:100%;padding:10px;background:#4da6ff;'
                                    f'color:white;border:none;border-radius:8px;cursor:pointer;">'
                                    f'Stripe</button></a>', unsafe_allow_html=True)
                    else:
                        st.info("Demo mode" if lang == "en" else "Stripe未設定のため、デモモードです。")
                        auth._update_plan(email, key, expires_at="2099-12-31T23:59:59")
                        st.rerun()

    if email and email != "guest":
        st.divider()
        check = auth.check_prediction_limit(email)
        remaining = ("Unlimited" if lang == "en" else "無制限") if check["remaining"] == -1 else f"{check['remaining']}"
        plan_name = current_plan.get("name_en", current_plan["name"]) if lang == "en" else current_plan["name"]
        c1, c2 = st.columns(2)
        c1.metric("Plan" if lang == "en" else "現在のプラン", plan_name)
        c2.metric("Remaining" if lang == "en" else "残り予測回数", remaining)


def render_user_badge():
    """サイドバー上部のユーザーバッジ"""
    email = st.session_state.get("user_email", "")
    if not email:
        return
    user = st.session_state.get("user", {})
    name = user.get("display_name", email.split("@")[0])
    plan = user.get("plan", "free")
    plan_info = PLANS.get(plan, PLANS["free"])
    lang = get_lang()
    plan_label = plan_info.get("name_en", plan_info["name"]) if lang == "en" else plan_info["name"]
    plan_color = {"free": "#8b949e", "pro": "#4da6ff", "premium": "#ffd000",
                  "admin": "#ff6b6b"}.get(plan, "#8b949e")

    st.markdown(f"""
    <div style="background:#161b22; border-radius:8px; padding:10px 14px; margin-bottom:12px;
                border:1px solid #30363d;">
        <div style="font-weight:bold; color:#c9d1d9;">{name}</div>
        <div style="font-size:0.8em; color:{plan_color};">{plan_label}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Logout" if lang == "en" else "ログアウト",
                 key="logout_btn", use_container_width=True):
        for key in ["user_email", "user", "last_prediction", "weights",
                     "last_updated", "backtest_result"]:
            st.session_state.pop(key, None)
        st.rerun()
