"""Общие функции для подготовки картинок под экран Kindle 4 (600x800, 16 оттенков серого)."""

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

KINDLE_W, KINDLE_H = 600, 800  # родная ориентация экрана Kindle 4 (портрет)
LEVELS = 16                    # e-ink панель Kindle 4 показывает 16 уровней серого


def target_size(orientation):
    """Размер, в котором рисуем картинку (до поворота под экран)."""
    if orientation == "landscape":
        return KINDLE_H, KINDLE_W  # 800x600
    return KINDLE_W, KINDLE_H      # 600x800


def _gray_palette(levels=LEVELS):
    pal = []
    for i in range(levels):
        v = round(i * 255 / (levels - 1))
        pal += [v, v, v]
    img = Image.new("P", (1, 1))
    img.putpalette(pal)
    return img


def quantize(img, dither):
    """Сводит картинку к 16 оттенкам серого.

    dither=True  — диффузия ошибки Флойда — Стейнберга (для фото: плавные градиенты).
    dither=False — простое округление (для интерфейса: чистые линии и текст).
    """
    gray = img.convert("L")
    if not dither:
        step = 255 / (LEVELS - 1)
        return gray.point(lambda v: int(round(round(v / step) * step)))
    q = gray.convert("RGB").quantize(
        palette=_gray_palette(), dither=Image.Dither.FLOYDSTEINBERG
    )
    return q.convert("L")


def enhance_photo(img, contrast=1.15, gamma=1.15, sharpen=True):
    """Подтягивает фото под e-ink: на бумажном экране всё выглядит темнее и мягче."""
    img = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    if contrast != 1:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if gamma != 1:
        inv = 1.0 / gamma  # gamma > 1 осветляет средние тона
        lut = [int(round(255 * ((i / 255) ** inv))) for i in range(256)]
        img = img.point(lut)
    if sharpen:
        img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=70, threshold=2))
    return img


def to_kindle(img, orientation, rotate=90):
    """Поворачивает горизонтальную картинку в родные 600x800 экрана."""
    if orientation == "landscape":
        img = img.rotate(rotate, expand=True)
    if img.size != (KINDLE_W, KINDLE_H):
        raise ValueError(f"ожидался размер {KINDLE_W}x{KINDLE_H}, получилось {img.size}")
    return img


def save_png(img, path):
    """8-битный PNG в оттенках серого без альфа-канала: такой понимают eips и linkss."""
    img.convert("L").save(path, format="PNG", optimize=True)
