"""icon.jpg のチェッカー柄背景を除去して透明PNGに変換
HSV色空間でロゴ（青〜シアン）の色だけ厳密に残す"""
from PIL import Image, ImageFilter, ImageOps
import numpy as np
import os

DIR = os.path.dirname(__file__)
src = os.path.join(DIR, "icon.jpg")

img = Image.open(src).convert("RGBA")
data = np.array(img, dtype=np.float32)
r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]

# --- HSV変換 ---
mx = np.maximum(np.maximum(r, g), b)
mn = np.minimum(np.minimum(r, g), b)
diff = mx - mn

sat = np.where(mx > 0, diff / mx, 0)

hue = np.zeros_like(r)
mask_r = (mx == r) & (diff > 0)
mask_g = (mx == g) & (diff > 0)
mask_b = (mx == b) & (diff > 0)
hue[mask_r] = 60 * (((g[mask_r] - b[mask_r]) / diff[mask_r]) % 6)
hue[mask_g] = 60 * (((b[mask_g] - r[mask_g]) / diff[mask_g]) + 2)
hue[mask_b] = 60 * (((r[mask_b] - g[mask_b]) / diff[mask_b]) + 4)

# --- ロゴ判定（青〜シアン系、彩度しっかり） ---
is_blue_cyan = (hue >= 150) & (hue <= 230) & (sat > 0.20) & (mx > 40)

# アルファマスク: 彩度に基づくソフトマスク
# 彩度が高いほど不透明、低いほど透明
alpha = np.zeros_like(r)
alpha[is_blue_cyan] = np.clip(sat[is_blue_cyan] * 400, 80, 255)

# --- マスクのクリーンアップ ---
alpha_img = Image.fromarray(alpha.astype(np.uint8), mode="L")

# 小さなノイズ除去（モルフォロジー的に開閉操作）
# MinFilter → 小さな白い点を除去 (erode)
alpha_img = alpha_img.filter(ImageFilter.MinFilter(3))
# MaxFilter → 穴を埋める (dilate)
alpha_img = alpha_img.filter(ImageFilter.MaxFilter(3))

# エッジを滑らかに
alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=1.2))

# コントラスト強調
alpha_arr = np.array(alpha_img, dtype=np.float32)
alpha_arr = np.clip((alpha_arr - 15) * (255 / 220), 0, 255)

data[:, :, 3] = alpha_arr
result = Image.fromarray(data.astype(np.uint8), mode="RGBA")

# 余白トリミング
bbox = result.getbbox()
if bbox:
    pad = 4
    x1 = max(0, bbox[0] - pad)
    y1 = max(0, bbox[1] - pad)
    x2 = min(result.width, bbox[2] + pad)
    y2 = min(result.height, bbox[3] + pad)
    result = result.crop((x1, y1, x2, y2))

result.save(os.path.join(DIR, "icon.png"), "PNG")
print(f"Transparent icon: {result.size[0]}x{result.size[1]}")

# ダークテーマ版（Streamlitの背景色）
dark = Image.new("RGBA", result.size, (14, 17, 23, 255))
dark.paste(result, (0, 0), result)
dark.save(os.path.join(DIR, "icon_dark.png"), "PNG")
print("Dark version saved!")
