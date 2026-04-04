"""ダークモード + レスポンシブCSS"""

VIEWPORT_META = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">'

CUSTOM_CSS = """
<style>
    .prediction-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px; padding: 24px;
        border: 1px solid #30363d; margin-bottom: 16px;
    }
    .prediction-card h2 { margin: 0 0 8px 0; font-size: 1.4em; }
    .prediction-card .price { font-size: 2.2em; font-weight: bold; margin: 8px 0; }
    .prediction-card .sub { color: #8b949e; font-size: 0.9em; }
    .prediction-card .sep { display: inline; }
    .bullish { color: #00d26a; font-weight: bold; }
    .bearish { color: #f8312f; font-weight: bold; }
    .neutral { color: #ffd000; font-weight: bold; }
    .metric-card {
        background: #161b22; border-radius: 8px; padding: 16px;
        text-align: center; border: 1px solid #30363d;
    }
    .metric-card .value { font-size: 1.8em; font-weight: bold; color: #4da6ff; }
    .metric-card .label { color: #8b949e; font-size: 0.85em; margin-top: 4px; }
    .gauge-container { text-align: center; margin: 20px 0; }
    .stTabs [data-baseweb="tab-panel"] { padding-top: 16px; }
    .stButton > button { width: 100%; border-radius: 8px; }

    /* ===== ツールバー・フッター・バッジ全非表示 ===== */
    [data-testid="stToolbar"] { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    [data-testid="manage-app-button"] { display: none !important; }
    .viewerBadge_container__r5tak { display: none !important; }
    .stApp > header { display: none !important; }
    ._container_gzau3_1 { display: none !important; }
    iframe[title="streamlit_lottie.streamlit_lottie"] { display: none !important; }
    /* 右下の全フローティングアイコン */
    div[data-testid="stBottomBlockContainer"] ~ div { display: none !important; }
    .st-emotion-cache-czk5ss { display: none !important; }
    .st-emotion-cache-164nlkn { display: none !important; }

    /* ===== スマホ対応 (768px以下) ===== */
    @media (max-width: 768px) {
        .block-container {
            padding: 0.8rem 0.5rem !important;
        }
        .prediction-card {
            padding: 14px 10px;
            border-radius: 8px;
        }
        .prediction-card h2 { font-size: 1.05em; }
        .prediction-card .price { font-size: 1.5em; }
        .prediction-card .price span { font-size: 0.6em !important; }
        .prediction-card .sub { font-size: 0.78em; line-height: 1.8; }
        .prediction-card .sep {
            display: block;
            height: 2px;
        }
        .metric-card {
            padding: 10px 6px;
            margin-bottom: 8px;
        }
        .metric-card .value { font-size: 1.3em; }
        .metric-card .label { font-size: 0.72em; }

        /* カラムを縦並びに */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }

        /* タブを横スクロール対応 */
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            flex-wrap: nowrap !important;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 0.78em;
            padding: 8px 10px;
            white-space: nowrap;
        }

        /* テーブル横スクロール */
        [data-testid="stDataFrame"] {
            overflow-x: auto;
        }

        /* サイドバー幅 */
        [data-testid="stSidebar"] {
            min-width: 250px !important;
            max-width: 85vw !important;
        }
    }
</style>
"""
