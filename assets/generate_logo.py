"""ロゴ画像生成スクリプト — 初回のみ実行"""
from PIL import Image, ImageDraw, ImageFont
import os

DIR = os.path.dirname(__file__)


def _create_icon(path: str, size: int = 256):
    """ファビコン / ページアイコン"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 丸い背景
    draw.ellipse([4, 4, size - 4, size - 4], fill="#0d1117", outline="#4da6ff", width=4)
    # "A" の文字
    try:
        font = ImageFont.truetype("arial.ttf", size // 2)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "A", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) / 2, (size - th) / 2 - 10), "A", fill="#4da6ff", font=font)
    # 株価チャート風の折れ線
    points = [
        (size * 0.2, size * 0.72),
        (size * 0.35, size * 0.58),
        (size * 0.5, size * 0.68),
        (size * 0.65, size * 0.48),
        (size * 0.8, size * 0.38),
    ]
    draw.line(points, fill="#00d26a", width=3)
    for p in points:
        r = 4
        draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill="#00d26a")
    img.save(path, "PNG")


def _create_sidebar_logo(path: str, w: int = 800, h: int = 160):
    """サイドバーロゴ（横長）"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # アイコン部分
    icon_size = h - 20
    ox, oy = 10, 10
    draw.rounded_rectangle([ox, oy, ox + icon_size, oy + icon_size],
                           radius=20, fill="#0d1117", outline="#4da6ff", width=3)
    try:
        icon_font = ImageFont.truetype("arial.ttf", icon_size // 2)
    except Exception:
        icon_font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "A", font=icon_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((ox + (icon_size - tw) / 2, oy + (icon_size - th) / 2 - 5),
              "A", fill="#4da6ff", font=icon_font)
    # チャートライン
    pts = [
        (ox + icon_size * 0.2, oy + icon_size * 0.78),
        (ox + icon_size * 0.4, oy + icon_size * 0.58),
        (ox + icon_size * 0.6, oy + icon_size * 0.68),
        (ox + icon_size * 0.8, oy + icon_size * 0.48),
    ]
    draw.line(pts, fill="#00d26a", width=3)
    # テキスト
    text_x = ox + icon_size + 18
    try:
        title_font = ImageFont.truetype("arial.ttf", 38)
        sub_font = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        title_font = ImageFont.load_default()
        sub_font = title_font
    draw.text((text_x, h // 2 - 35), "Alpha-AutoLearn", fill="#e6edf3", font=title_font)
    draw.text((text_x, h // 2 + 15), "AI Stock Prediction", fill="#8b949e", font=sub_font)
    img.save(path, "PNG")


if __name__ == "__main__":
    _create_icon(os.path.join(DIR, "icon.png"))
    _create_sidebar_logo(os.path.join(DIR, "logo.png"))
    _create_sidebar_logo(os.path.join(DIR, "logo_small.png"), 200, 50)
    print("Logo files generated!")
