@echo off
chcp 65001 >nul
title Alpha-AutoLearn AI株価予測システム

echo ========================================
echo   Alpha-AutoLearn AI株価予測システム
echo ========================================
echo.

REM Pythonの確認
python --version >nul 2>&1
if errorlevel 1 (
    echo [エラー] Pythonが見つかりません。
    echo Python 3.10以上をインストールしてください:
    echo   https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM プロジェクトディレクトリに移動
cd /d "%~dp0"

REM 仮想環境のセットアップ
if not exist ".venv" (
    echo [初回セットアップ] 仮想環境を作成中...
    python -m venv .venv
    if errorlevel 1 (
        echo [エラー] 仮想環境の作成に失敗しました。
        pause
        exit /b 1
    )
    echo.

    call .venv\Scripts\activate.bat

    echo [初回セットアップ] 依存パッケージをインストール中...
    echo   (初回は数分かかります)
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [エラー] パッケージのインストールに失敗しました。
        pause
        exit /b 1
    )
    echo.

    echo [初回セットアップ] CmdStan をインストール中...
    echo   (Prophet の実行に必要です。5-10分かかる場合があります)
    echo.
    python setup_cmdstan.py
    echo.
) else (
    call .venv\Scripts\activate.bat
)

REM SSL証明書のパス修正 (日本語フォルダ名対策)
if not exist "%USERPROFILE%\cacert.pem" (
    copy ".venv\Lib\site-packages\certifi\cacert.pem" "%USERPROFILE%\cacert.pem" >nul 2>&1
)
set CURL_CA_BUNDLE=%USERPROFILE%\cacert.pem
set REQUESTS_CA_BUNDLE=%USERPROFILE%\cacert.pem

echo.
echo ----------------------------------------
echo   起動中...
echo   ブラウザで http://localhost:8501 を開いてください
echo   終了するにはこのウィンドウを閉じてください
echo ----------------------------------------
echo.

streamlit run app.py
