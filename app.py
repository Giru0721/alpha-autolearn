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

import time
import streamlit as st
from PIL import Image
from ui.styles import CUSTOM_CSS, VIEWPORT_META
from ui.layout import render_sidebar, render_main_content
from ui.auth_ui import render_auth_page, render_user_badge, render_subscription_page, get_auth_manager
from ui.i18n import TEXTS
from feedback.database import Database

_ICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
_SESSION_SECRET = "alpha-autolearn-2024"
_TOKEN_MAX_AGE_DAYS = 30


def _make_token(email: str) -> str:
    """日単位のタイムスタンプ付きトークン生成（30日有効）"""
    day = int(time.time()) // 86400
    return hashlib.sha256(f"{_SESSION_SECRET}:{email}:{day}".encode()).hexdigest()[:16]


def _verify_token(email: str, token: str) -> bool:
    """トークン検証（過去30日以内に生成されたものを受け入れ）"""
    current_day = int(time.time()) // 86400
    for offset in range(_TOKEN_MAX_AGE_DAYS + 1):
        day = current_day - offset
        expected = hashlib.sha256(f"{_SESSION_SECRET}:{email}:{day}".encode()).hexdigest()[:16]
        if token == expected:
            return True
    return False


def _try_restore_session():
    """クエリパラメータからセッション復元"""
    if "user_email" in st.session_state:
        return
    params = st.query_params
    token = params.get("t", "")
    email = params.get("u", "")
    if email and token and _verify_token(email, token):
        auth = get_auth_manager()
        user = auth.get_user(email)
        if user:
            st.session_state["user_email"] = email
            st.session_state["user"] = user


def _save_session_to_params(email: str):
    """ログイン後にクエリパラメータにセッション保存"""
    new_token = _make_token(email)
    if st.query_params.get("u") == email and st.query_params.get("t") == new_token:
        return
    st.query_params["u"] = email
    st.query_params["t"] = new_token


def _inject_combined_js(is_logout: bool = False):
    """統合JavaScript: UI非表示 + ログイン保持(localStorage) + SEOメタタグ"""
    import streamlit.components.v1 as _components

    logout_flag = "true" if is_logout else "false"

    _components.html(f"""
    <script>
    (function() {{
        var pd = window.parent.document;

        // ===== SEO メタタグ =====
        var metas = [
            {{name:'description', content:'Alpha-AutoLearn - AI機械学習による株価予測システム。複数のAIモデルを組み合わせたアンサンブル予測で高精度な株価分析を提供。'}},
            {{name:'keywords', content:'AI株価予測,AI株式予想,機械学習,株式投資,アンサンブル学習,株価分析,Alpha-AutoLearn,プラスアルファ,stock prediction,AI investment'}},
            {{property:'og:title', content:'Alpha-AutoLearn - AI株価予測システム'}},
            {{property:'og:description', content:'AI機械学習で高精度な株価予測。日本株・米国株対応。'}},
            {{property:'og:type', content:'website'}},
            {{name:'apple-mobile-web-app-capable', content:'yes'}},
            {{name:'apple-mobile-web-app-status-bar-style', content:'black-translucent'}},
            {{name:'apple-mobile-web-app-title', content:'AutoLearn'}},
            {{name:'theme-color', content:'#4da6ff'}}
        ];
        metas.forEach(function(m) {{
            var el = pd.createElement('meta');
            Object.keys(m).forEach(function(k) {{ el.setAttribute(k, m[k]); }});
            pd.head.appendChild(el);
        }});

        // ===== PWA: manifest + Service Worker =====
        if (!pd.querySelector('link[rel="manifest"]')) {{
            var manifestLink = pd.createElement('link');
            manifestLink.rel = 'manifest';
            manifestLink.href = '/_app/static/manifest.json';
            pd.head.appendChild(manifestLink);

            var appleIcon = pd.createElement('link');
            appleIcon.rel = 'apple-touch-icon';
            appleIcon.href = '/_app/static/icon-192.png';
            pd.head.appendChild(appleIcon);
        }}
        try {{
            if ('serviceWorker' in window.parent.navigator) {{
                window.parent.navigator.serviceWorker.register('/_app/static/sw.js')
                    .catch(function() {{}});
            }}
        }} catch(e) {{}}

        // ===== ログイン保持 (localStorage) =====
        try {{
            var url = new URL(window.parent.location);
            if ({logout_flag}) {{
                // ログアウト → localStorage 削除
                window.parent.localStorage.removeItem('alpha_user');
                window.parent.localStorage.removeItem('alpha_token');
            }} else if (!url.searchParams.get('u')) {{
                // URLにユーザー情報なし → localStorageから復元
                var savedEmail = window.parent.localStorage.getItem('alpha_user');
                var savedToken = window.parent.localStorage.getItem('alpha_token');
                if (savedEmail && savedToken) {{
                    url.searchParams.set('u', savedEmail);
                    url.searchParams.set('t', savedToken);
                    window.parent.location.replace(url.toString());
                    return;
                }}
            }} else {{
                // ログイン中 → localStorageに保存
                var email = url.searchParams.get('u');
                var token = url.searchParams.get('t');
                if (email && token) {{
                    window.parent.localStorage.setItem('alpha_user', email);
                    window.parent.localStorage.setItem('alpha_token', token);
                }}
            }}
        }} catch(e) {{}}

        // ===== Streamlit UI非表示 =====
        function hideStuff() {{
            try {{
                pd.querySelectorAll('*').forEach(function(el) {{
                    var s = window.getComputedStyle(el);
                    if (s.position === 'fixed') {{
                        var r = el.getBoundingClientRect();
                        if (r.bottom > (window.innerHeight - 80) && r.right > (window.innerWidth - 200)) {{
                            if (!el.getAttribute('data-testid') ||
                                el.getAttribute('data-testid').indexOf('Sidebar') < 0) {{
                                el.style.display = 'none';
                            }}
                        }}
                    }}
                }});
                pd.querySelectorAll('a[href*="github"]').forEach(function(el) {{
                    el.style.display = 'none';
                }});
                pd.querySelectorAll('[data-testid="stToolbarActions"] > div').forEach(function(el) {{
                    if (el.querySelector('a') || el.innerHTML.indexOf('github') >= 0 ||
                        el.innerHTML.indexOf('fork') >= 0) {{
                        el.style.display = 'none';
                    }}
                }});
            }} catch(e) {{}}
        }}
        setTimeout(hideStuff, 500);
        setTimeout(hideStuff, 1500);
        setTimeout(hideStuff, 4000);
        setInterval(hideStuff, 10000);
    }})();
    </script>
    """, height=0)


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

    # Stripe API で検証（安全な方法のみ使用）
    result = auth.verify_checkout_session(session_id)
    if result:
        upgraded = True
        email = result["email"]
    else:
        # Stripe検証失敗 → ログに記録（手動同期ボタンで対応可能）
        print(f"[Stripe] checkout session verification failed: {session_id}")
        email = st.query_params.get("u", "")

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
        st.rerun()
    else:
        # 検証失敗でもパラメータは除去
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
        initial_sidebar_state="expanded",
    )
    st.markdown(VIEWPORT_META, unsafe_allow_html=True)
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # ログアウト信号チェック
    _is_logout = st.query_params.get("logout") == "1"
    if _is_logout:
        try:
            del st.query_params["logout"]
        except Exception:
            pass

    # 統合JS: UI非表示 + ログイン保持 + SEOメタタグ
    _inject_combined_js(is_logout=_is_logout)

    if "db" not in st.session_state:
        st.session_state["db"] = Database()

    # セッション復元（ログアウト直後はスキップ）
    if not _is_logout:
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
