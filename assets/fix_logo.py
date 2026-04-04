"""ロゴの白背景を完全除去 — rembg (AI) + 手動フォールバック"""
from PIL import Image
import os, shutil

DIR = os.path.dirname(__file__)
src = r"C:\Users\maehara\Downloads\Gemini_Generated_Image_ktj8gqktj8gqktj8 (2).png"
if not os.path.exists(src):
    src = os.path.join(DIR, "icon_src.png")

img = Image.open(src).convert("RGBA")

# rembg で AI 背景除去
try:
    from rembg import remove
    result = remove(img)
    print("Used rembg (AI) for background removal")
except ImportError:
    print("rembg not available, using manual method")
    import numpy as np
    from PIL import ImageFilter
    from collections import deque
    data = np.array(img, dtype=np.uint8)
    r, g, b = data[:,:,0].astype(float), data[:,:,1].astype(float), data[:,:,2].astype(float)
    white_dist = np.sqrt((255-r)**2 + (255-g)**2 + (255-b)**2)
    h, w = data.shape[:2]
    visited = np.zeros((h, w), dtype=bool)
    bg_mask = np.zeros((h, w), dtype=bool)
    seeds = [(y, x) for x in range(w) for y in [0, h-1]]
    seeds += [(y, x) for y in range(h) for x in [0, w-1]]
    queue = deque()
    for (y, x) in seeds:
        if white_dist[y, x] < 90 and not visited[y, x]:
            queue.append((y, x)); visited[y, x] = True; bg_mask[y, x] = True
    while queue:
        cy, cx = queue.popleft()
        for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            ny, nx = cy+dy, cx+dx
            if 0<=ny<h and 0<=nx<w and not visited[ny,nx]:
                visited[ny,nx] = True
                if white_dist[ny,nx] < 90:
                    bg_mask[ny,nx] = True; queue.append((ny,nx))
    bg_img = Image.fromarray((bg_mask*255).astype(np.uint8), mode="L")
    for _ in range(3):
        bg_img = bg_img.filter(ImageFilter.MaxFilter(5))
    alpha = np.where(np.array(bg_img) > 128, 0, 255).astype(np.uint8)
    data[:,:,3] = alpha
    result = Image.fromarray(data, mode="RGBA")

# トリミング
bbox = result.getbbox()
if bbox:
    pad = 6
    x1, y1 = max(0, bbox[0]-pad), max(0, bbox[1]-pad)
    x2, y2 = min(result.width, bbox[2]+pad), min(result.height, bbox[3]+pad)
    result = result.crop((x1, y1, x2, y2))

result.save(os.path.join(DIR, "icon.png"), "PNG")
print(f"Transparent: {result.size[0]}x{result.size[1]}")

# ダークテーマ版
dark = Image.new("RGBA", result.size, (14, 17, 23, 255))
dark.paste(result, (0, 0), result)
dark.save(os.path.join(DIR, "icon_dark.png"), "PNG")
print("Dark version saved!")

shutil.copy2(src, os.path.join(DIR, "icon_src.png"))
