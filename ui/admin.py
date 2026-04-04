"""管理者パネルUI"""

import streamlit as st
import pandas as pd

from auth.subscription import AuthManager, PLANS
from ui.i18n import T


def render_admin_page():
    """管理者パネル"""
    user = st.session_state.get("user", {})
    if user.get("role") != "admin":
        st.error("Access denied")
        return

    auth = AuthManager()
    st.markdown(f"### {T('admin_panel')}")

    # ユーザー統計
    users = auth.get_all_users()
    total = len(users)
    plan_counts = {}
    for u in users:
        p = u.get("plan", "free")
        plan_counts[p] = plan_counts.get(p, 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(T("total_users"), total)
    c2.metric("Free", plan_counts.get("free", 0))
    c3.metric("Pro", plan_counts.get("pro", 0))
    c4.metric("Premium", plan_counts.get("premium", 0))

    st.divider()

    # ユーザー一覧
    st.markdown(f"#### {T('user_management')}")
    if users:
        df = pd.DataFrame(users)
        col_rename = {
            "id": "ID", "email": "Email", "display_name": "Name",
            "role": "Role", "plan": "Plan",
            "predictions_today": "Today", "created_at": "Registered",
        }
        display_cols = [c for c in col_rename.keys() if c in df.columns]
        st.dataframe(df[display_cols].rename(columns=col_rename),
                     use_container_width=True, hide_index=True)

        # プラン変更
        st.markdown("##### Change User Plan")
        with st.form("admin_plan_form"):
            target_email = st.selectbox("User", [u["email"] for u in users if u["role"] != "admin"])
            new_plan = st.selectbox("Plan", ["free", "pro", "premium"])
            if st.form_submit_button("Update", type="primary"):
                auth.update_user_plan(target_email, new_plan)
                st.success(f"{target_email} -> {new_plan}")
                st.rerun()

        # ユーザー削除
        st.markdown("##### Delete User")
        with st.form("admin_delete_form"):
            del_email = st.selectbox("User", [u["email"] for u in users if u["role"] != "admin"],
                                     key="del_user_select")
            if st.form_submit_button("Delete", type="secondary"):
                auth.delete_user(del_email)
                st.success(f"Deleted: {del_email}")
                st.rerun()

    # Stripe設定状況
    st.divider()
    st.markdown("#### Stripe Status")
    import os
    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if stripe_key:
        st.success("Stripe API Key: configured")
    else:
        st.warning("Stripe API Key: not set")
        st.markdown("""
        **Streamlit Cloud Secrets** に以下を設定してください:
        ```toml
        STRIPE_SECRET_KEY = "sk_live_..."
        STRIPE_PUBLISHABLE_KEY = "pk_live_..."
        STRIPE_PRO_PRICE_ID = "price_..."
        STRIPE_PREMIUM_PRICE_ID = "price_..."
        STRIPE_WEBHOOK_SECRET = "whsec_..."
        ```
        """)

    st.markdown("""
    **収益の受取方法:**
    1. [Stripe Dashboard](https://dashboard.stripe.com) にログイン
    2. 設定 > 銀行口座 で日本の銀行口座を登録
    3. Visa / Mastercard / JCB / American Express が自動対応
    4. PayPayはStripe Link経由で対応可能
    """)
