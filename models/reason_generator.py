"""予測理由の自動生成 - テクニカル指標とモデル出力から根拠テキストを作成"""

import pandas as pd
import numpy as np


def generate_prediction_reason(feature_matrix: pd.DataFrame,
                                prediction: dict,
                                lang: str = "ja") -> str:
    """予測結果の根拠を自動生成する。

    feature_matrix: テクニカル指標付きのDataFrame（最終行を分析）
    prediction: EnsemblePredictor.train_and_predict() の戻り値
    lang: "ja" or "en"
    """
    if feature_matrix.empty:
        return ""

    latest = feature_matrix.iloc[-1]
    signals = []

    # --- 1. RSI ---
    rsi = _safe_get(latest, "RSI_14")
    if rsi is not None:
        if rsi < 30:
            signals.append(_t(lang,
                              f"RSIが{rsi:.0f}と売られすぎ水準（反発シグナル）",
                              f"RSI at {rsi:.0f} — oversold zone (reversal signal)"))
        elif rsi > 70:
            signals.append(_t(lang,
                              f"RSIが{rsi:.0f}と買われすぎ水準（調整リスク）",
                              f"RSI at {rsi:.0f} — overbought zone (correction risk)"))
        elif 45 <= rsi <= 55:
            signals.append(_t(lang,
                              f"RSI {rsi:.0f}で中立圏",
                              f"RSI at {rsi:.0f} — neutral"))

    # --- 2. MACD ---
    macd_hist = _safe_get(latest, "MACD_hist")
    macd_cross_up = _safe_get(latest, "MACD_cross_up")
    macd_cross_down = _safe_get(latest, "MACD_cross_down")
    if macd_cross_up and macd_cross_up > 0:
        signals.append(_t(lang,
                          "MACD���ゴールデンクロス（上昇転換）",
                          "MACD golden cross (bullish reversal)"))
    elif macd_cross_down and macd_cross_down > 0:
        signals.append(_t(lang,
                          "MACDがデッドクロス（下降転換）",
                          "MACD death cross (bearish reversal)"))
    elif macd_hist is not None:
        if macd_hist > 0:
            signals.append(_t(lang,
                              "MACDヒストグラムがプラス圏（上昇勢い継続）",
                              "MACD histogram positive (bullish momentum)"))
        else:
            signals.append(_t(lang,
                              "MACD��ストグラムがマイナス圏（下落圧力）",
                              "MACD histogram negative (bearish pressure)"))

    # --- 3. 移動平均線 ---
    sma20_above_50 = _safe_get(latest, "SMA20_above_50")
    dist_sma20 = _safe_get(latest, "Dist_SMA20")
    if dist_sma20 is not None:
        pct = dist_sma20 * 100
        if pct > 5:
            signals.append(_t(lang,
                              f"株価がSMA20を{pct:.1f}%上���っている（過熱感）",
                              f"Price {pct:.1f}% above SMA20 (overextended)"))
        elif pct < -5:
            signals.append(_t(lang,
                              f"株価がSMA20を{abs(pct):.1f}%下回っている（割安圏）",
                              f"Price {abs(pct):.1f}% below SMA20 (undervalued zone)"))
    if sma20_above_50 is not None:
        if sma20_above_50 > 0:
            signals.append(_t(lang,
                              "短期MA>中期MA（上昇トレンド維持）",
                              "Short-term MA above mid-term MA (uptrend intact)"))
        else:
            signals.append(_t(lang,
                              "短期MA<中期MA（下降トレンド）",
                              "Short-term MA below mid-term MA (downtrend)"))

    # --- 4. ボリンジャーバンド ---
    bb_pct = _safe_get(latest, "BB_pct")
    bb_squeeze = _safe_get(latest, "BB_squeeze")
    if bb_squeeze and bb_squeeze > 0:
        signals.append(_t(lang,
                          "ボリンジャーバンドがスクイーズ中（大きな動きの前兆）",
                          "Bollinger Band squeeze (big move ahead)"))
    elif bb_pct is not None:
        if bb_pct > 1.0:
            signals.append(_t(lang,
                              "株価がボリンジャー上限を突破（強い上昇 or 過熱）",
                              "Price above upper Bollinger Band (strong rally or overbought)"))
        elif bb_pct < 0.0:
            signals.append(_t(lang,
                              "株価がボリンジャー下限を割り込み（売られすぎ or 急落）",
                              "Price below lower Bollinger Band (oversold or breakdown)"))

    # --- 5. 出来高 ---
    vol_spike = _safe_get(latest, "Vol_spike")
    vol_ratio = _safe_get(latest, "Volume_ratio")
    if vol_spike and vol_spike > 0:
        signals.append(_t(lang,
                          f"出来高が平均の{vol_ratio:.1f}倍に急増（転換点の可能性）",
                          f"Volume surged to {vol_ratio:.1f}x average (potential turning point)"))

    # --- 6. ADXトレンド強度 ---
    adx = _safe_get(latest, "ADX_14")
    trend_dir = _safe_get(latest, "Trend_strength_dir")
    if adx is not None:
        if adx > 25:
            if trend_dir and trend_dir > 0:
                signals.append(_t(lang,
                                  f"ADX={adx:.0f}で強い上昇ト��ンド",
                                  f"ADX={adx:.0f} — strong uptrend"))
            elif trend_dir and trend_dir < 0:
                signals.append(_t(lang,
                                  f"ADX={adx:.0f}で強い下降トレンド",
                                  f"ADX={adx:.0f} — strong downtrend"))
        elif adx < 20:
            signals.append(_t(lang,
                              f"ADX={adx:.0f}でトレンドが弱い（レンジ相場）",
                              f"ADX={adx:.0f} — weak trend (range-bound)"))

    # --- 7. モメンタム ---
    momentum = _safe_get(latest, "Momentum_align")
    if momentum is not None:
        if momentum > 0.7:
            signals.append(_t(lang,
                              "短期・中期・長期リターンが揃って上昇方向",
                              "Short/mid/long-term returns all aligned upward"))
        elif momentum < 0.3:
            signals.append(_t(lang,
                              "短期・中期・長期リターンが揃って下落方向",
                              "Short/mid/long-term returns all aligned downward"))

    # --- 8. モデル一致性 ---
    pp = prediction.get("prophet_price", 0)
    xp = prediction.get("xgboost_price", 0)
    cp = prediction.get("current_price", 0)
    if cp > 0:
        p_dir = "up" if pp > cp else "down"
        x_dir = "up" if xp > cp else "down"
        if p_dir == x_dir:
            if p_dir == "up":
                signals.append(_t(lang,
                                  "ProphetとXGBoostの両モデルが上昇を予測（信頼度高）",
                                  "Both Prophet and XGBoost predict upside (high confidence)"))
            else:
                signals.append(_t(lang,
                                  "ProphetとXGBoostの両モデルが下落を予測（信頼度高）",
                                  "Both Prophet and XGBoost predict downside (high confidence)"))
        else:
            signals.append(_t(lang,
                              "ProphetとXGBoostで方向が分かれている（不確実性高）",
                              "Prophet and XGBoost disagree on direction (higher uncertainty)"))

    # --- 9. 直近勝率 ---
    wr5 = _safe_get(latest, "WinRatio_5d")
    if wr5 is not None:
        if wr5 > 0.7:
            signals.append(_t(lang,
                              f"直近5日中{wr5*5:.0f}日上昇（短期強気）",
                              f"{wr5*5:.0f} of last 5 days positive (short-term bullish)"))
        elif wr5 < 0.3:
            signals.append(_t(lang,
                              f"直近5日中{wr5*5:.0f}日しか上昇していない（短期弱気���",
                              f"Only {wr5*5:.0f} of last 5 days positive (short-term bearish)"))

    # --- まとめ ---
    if not signals:
        return _t(lang,
                  "特筆すべきシグナルなし。市場は安定推移中。",
                  "No notable signals. Market trending steadily.")

    # 最大5つまで選択（最重要なものを優先）
    selected = signals[:5]

    # 方向の総括
    direction = prediction.get("direction", "neutral")
    ret = prediction.get("predicted_return", 0)
    horizon = prediction.get("horizon", 5)

    if direction == "bullish":
        summary = _t(lang,
                     f"▲ {horizon}日後の上昇を予測。根拠：",
                     f"▲ Predicted to rise in {horizon} days. Reasons:")
    elif direction == "bearish":
        summary = _t(lang,
                     f"▼ {horizon}日後の下落を予測。根拠：",
                     f"▼ Predicted to decline in {horizon} days. Reasons:")
    else:
        summary = _t(lang,
                     f"◆ {horizon}日後は横ばいを予測。根拠：",
                     f"◆ Predicted sideways movement in {horizon} days. Reasons:")

    bullet = "\n".join(f"• {s}" for s in selected)
    return f"{summary}\n{bullet}"


def _safe_get(row, col):
    """行からカラム値を安全に取得。NaN/存在しない場合はNone。"""
    try:
        val = row.get(col, None) if hasattr(row, 'get') else row[col]
        if val is not None and not (isinstance(val, float) and np.isnan(val)):
            return float(val)
    except (KeyError, TypeError, ValueError):
        pass
    return None


def _t(lang, ja, en):
    """言語切替ヘルパー"""
    return ja if lang == "ja" else en
