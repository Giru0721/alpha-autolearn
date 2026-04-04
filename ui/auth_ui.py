"""認証・サブスクリプションUI"""

import streamlit as st
from auth.subscription import AuthManager, PLANS


def get_auth_manager():
    if "auth_manager" not in st.session_state:
        st.session_state["auth_manager"] = AuthManager()
    return st.session_state["auth_manager"]


def render_auth_page():
    """ログイン/新規登録ページ"""
    st.markdown("### 🔐 ログイン / 新規登録")
    tab_login, tab_register = st.tabs(["ログイン", "新規登録"])

    with tab_login:
        email = st.text_input("メールアドレス", key="login_email")
        password = st.text_input("パスワード", type="password", key="login_pw")
        if st.button("ログイン", type="primary", use_container_width=True, key="login_btn"):
            if not email or not password:
                st.error("メールアドレスとパスワードを入力してください")
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
        new_email = st.text_input("メールアドレス", key="reg_email")
        new_name = st.text_input("表示名（任意）", key="reg_name")
        new_pw = st.text_input("パスワード（8文字以上）", type="password", key="reg_pw")
        new_pw2 = st.text_input("パスワード確認", type="password", key="reg_pw2")
        if st.button("無料で登録", type="primary", use_container_width=True, key="reg_btn"):
            if not new_email or not new_pw:
                st.error("メールアドレスとパスワードを入力してください")
                return
            if len(new_pw) < 8:
                st.error("パスワードは8文字以上にしてください")
                return
            if new_pw != new_pw2:
                st.error("パスワードが一致しません")
                return
            auth = get_auth_manager()
            result = auth.register(new_email, new_pw, new_name)
            if result["success"]:
                st.success("登録完了！ログインしてください。")
            else:
                st.error(result["message"])

    # ゲストモード
    st.divider()
    if st.button("ゲストとして続ける（制限あり）", use_container_width=True, key="guest_btn"):
        st.session_state["user_email"] = "guest"
        st.session_state["user"] = {"plan": "free", "display_name": "ゲスト", "email": "guest"}
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

    st.markdown("### 📋 プラン選択")
    cols = st.columns(3)

    for col, (key, plan) in zip(cols, PLANS.items()):
        with col:
            is_current = (key == current_key)
            border = "2px solid #4da6ff" if is_current else "1px solid #30363d"
            badge = "✅ 現在のプラン" if is_current else ""

            price_text = "無料" if plan["price"] == 0 else f"¥{plan['price']:,}/月"
            limit_text = "無制限" if plan["predictions_per_day"] == -1 else f"{plan['predictions_per_day']}回/日"

            features_html = "".join(f"<li>{f}</li>" for f in plan["features"])

            st.markdown(f"""
            <div style="background:#161b22; border-radius:12px; padding:20px; border:{border};
                        text-align:center; min-height:380px;">
                <div style="font-size:0.8em; color:#4da6ff; min-height:20px;">{badge}</div>
                <h3 style="margin:8px 0;">{plan['name']}</h3>
                <div style="font-size:1.8em; font-weight:bold; color:#4da6ff; margin:12px 0;">
                    {price_text}
                </div>
                <div style="color:#8b949e; margin-bottom:12px;">予測: {limit_text}</div>
                <ul style="text-align:left; color:#c9d1d9; font-size:0.85em; padding-left:20px;">
                    {features_html}
                </ul>
            </div>
            """, unsafe_allow_html=True)

            if not is_current and key != "free" and email and email != "guest":
                if st.button(f"{plan['name']}にアップグレード", key=f"upgrade_{key}",
                             use_container_width=True):
                    app_url = st.session_state.get("app_url", "http://localhost:8501")
                    checkout_url = auth.create_checkout_session(
                        email, key, app_url, app_url)
                    if checkout_url:
                        st.markdown(f'<a href="{checkout_url}" target="_blank">'
                                    f'<button style="width:100%;padding:10px;background:#4da6ff;'
                                    f'color:white;border:none;border-radius:8px;cursor:pointer;">'
                                    f'Stripe決済ページへ</button></a>', unsafe_allow_html=True)
                    else:
                        st.info("Stripe未設定のため、現在はデモモードです。全機能が利用可能です。")
                        auth._update_plan(email, key,
                                          expires_at="2099-12-31T23:59:59")
                        st.rerun()

    # 現在の利用状況
    if email and email != "guest":
        st.divider()
        st.markdown("### 📊 利用状況")
        check = auth.check_prediction_limit(email)
        remaining = "無制限" if check["remaining"] == -1 else f"{check['remaining']}回"
        c1, c2 = st.columns(2)
        c1.metric("現在のプラン", current_plan["name"])
        c2.metric("本日の残り予測回数", remaining)


def render_user_badge():
    """サイドバー上部のユーザーバッジ"""
    email = st.session_state.get("user_email", "")
    if not email:
        return
    user = st.session_state.get("user", {})
    name = user.get("display_name", email.split("@")[0])
    plan = user.get("plan", "free")
    plan_label = PLANS.get(plan, PLANS["free"])["name"]

    plan_color = {"free": "#8b949e", "pro": "#4da6ff", "premium": "#ffd000"}.get(plan, "#8b949e")

    st.markdown(f"""
    <div style="background:#161b22; border-radius:8px; padding:10px 14px; margin-bottom:12px;
                border:1px solid #30363d;">
        <div style="font-weight:bold; color:#c9d1d9;">{name}</div>
        <div style="font-size:0.8em; color:{plan_color};">{plan_label}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("ログアウト", key="logout_btn", use_container_width=True):
        for key in ["user_email", "user", "last_prediction", "weights", "last_updated"]:
            st.session_state.pop(key, None)
        st.rerun()
