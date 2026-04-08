FROM python:3.11-slim

WORKDIR /app

# システム依存パッケージ
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# 依存パッケージインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CmdStan（Prophet用）
RUN python -c "import cmdstanpy; cmdstanpy.install_cmdstan()"

# アプリケーションコード
COPY . .

# データ永続化ディレクトリ
RUN mkdir -p /data

# Streamlit設定
EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--browser.gatherUsageStats=false"]
