"""Alpha-AutoLearn - AI株価予測システム メインエントリーポイント"""

import sys
import os

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
from ui.auth_ui import render_auth_page, render_user_badge, render_subscription_page
from ui.i18n import TEXTS
from feedback.database import Database

_ICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "icon.png")


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

    # 認証チェック
    if "user_email" not in st.session_state:
        render_auth_page()
        return

    # メインアプリ
    settings = render_sidebar()

    # サブスクリプションタブが選ばれた場合
    if settings.get("show_subscription"):
        render_subscription_page()
    else:
        render_main_content(settings)


if __name__ == "__main__":
    main()
