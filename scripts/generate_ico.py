from PIL import Image
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
png_path = BASE_DIR / "assets" / "app_icon.png"
ico_path = BASE_DIR / "assets" / "app_icon.ico"

if png_path.exists():
    img = Image.open(png_path)
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format="ICO", sizes=icon_sizes)
    print("[ICO Generator] Successfully created app_icon.ico")
else:
    print("[ICO Generator] PNG icon not found")
