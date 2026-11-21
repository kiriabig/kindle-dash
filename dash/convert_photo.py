"""Конвертер любого фото в картинку для Kindle 4.

Пример:
    python3 dash/convert_photo.py photos/cat.jpg -o out/cat.png
    python3 dash/convert_photo.py photos/sea.jpg --landscape --fit pad
"""

import argparse
import os
import sys

from PIL import Image, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eink  # noqa: E402

try:  # фото с iPhone в HEIC: нужен пакет pillow-heif (pip install pillow-heif)
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

PHOTO_EXT = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tif", ".tiff", ".bmp", ".gif")


def latest_photo(folder):
    files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(PHOTO_EXT) and not f.startswith(".")
    ]
    if not files:
        raise FileNotFoundError(f"в папке {folder} нет фотографий")
    return max(files, key=os.path.getmtime)


def prepare_photo(path, orientation="portrait", fit="crop", contrast=1.15, gamma=1.15,
                  sharpen=True, background=255, focus=(0.5, 0.5)):
    """Возвращает картинку в оттенках серого размером под экран (до поворота)."""
    size = eink.target_size(orientation)
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # учитываем поворот с телефона

    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img)
    img = img.convert("L")

    if fit == "crop":  # заполняем весь экран; focus — какая точка кадра остаётся в центре (0..1)
        img = ImageOps.fit(img, size, Image.Resampling.LANCZOS, centering=focus)
        img = eink.enhance_photo(img, contrast, gamma, sharpen)
    else:              # вписываем целиком, по краям белые поля
        img = ImageOps.contain(img, size, Image.Resampling.LANCZOS)
        img = eink.enhance_photo(img, contrast, gamma, sharpen)
        img = ImageOps.pad(img, size, color=background)

    return eink.quantize(img, dither=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("photo", help="файл фото или папка (возьмётся самое свежее фото)")
    p.add_argument("-o", "--output", default="out/dash.png")
    p.add_argument("--landscape", action="store_true", help="горизонтально 800x600")
    p.add_argument("--rotate", type=int, default=90, choices=(90, 270))
    p.add_argument("--fit", choices=("crop", "pad"), default="crop")
    p.add_argument("--contrast", type=float, default=1.15)
    p.add_argument("--gamma", type=float, default=1.15)
    p.add_argument("--no-sharpen", action="store_true")
    p.add_argument("--focus", default="0.5,0.5",
                   help="что оставить при обрезке: X,Y от 0 до 1 (0.5,0.7 — центр по ширине, ниже середины)")
    a = p.parse_args()
    focus = tuple(float(v) for v in a.focus.split(","))

    path = latest_photo(a.photo) if os.path.isdir(a.photo) else a.photo
    orientation = "landscape" if a.landscape else "portrait"
    img = prepare_photo(path, orientation, a.fit, a.contrast, a.gamma, not a.no_sharpen, focus=focus)
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    eink.save_png(eink.to_kindle(img, orientation, a.rotate), a.output)
    print(f"{path} -> {a.output}")


if __name__ == "__main__":
    main()
