"""Собирает картинку для Kindle по config.ini: погоду или фото.

    python3 dash/build.py                     # -> out/dash.png
    python3 dash/build.py --sample            # погода на тестовых данных, без интернета
    python3 dash/build.py --mode photo        # переопределить режим из config.ini
"""

import argparse
import configparser
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import convert_photo  # noqa: E402
import eink  # noqa: E402
import render_weather  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default=os.path.join(ROOT, "config.ini"))
    p.add_argument("--mode", choices=("weather", "photo"))
    p.add_argument("--sample", action="store_true")
    p.add_argument("-o", "--output", default=os.path.join(ROOT, "out", "dash.png"),
                   help="картинка для Kindle (всегда 600×800)")
    p.add_argument("--preview", help="та же картинка без поворота, чтобы посмотреть глазами")
    a = p.parse_args()

    cfg = configparser.ConfigParser(inline_comment_prefixes=(";",))
    cfg.read(a.config, encoding="utf-8")
    dash = cfg["dashboard"]
    mode = a.mode or dash.get("mode", "weather").strip()
    orientation = dash.get("orientation", "portrait").strip()
    rotate = dash.getint("rotate", 90)
    lang = dash.get("language", "ru").strip()

    if mode == "photo":
        ph = cfg["photo"]
        folder = os.path.join(ROOT, "photos")
        name = ph.get("file", "").strip()
        path = os.path.join(folder, name) if name else convert_photo.latest_photo(folder)
        img = convert_photo.prepare_photo(
            path, orientation, ph.get("fit", "crop").strip(),
            ph.getfloat("contrast", 1.15), ph.getfloat("gamma", 1.15), ph.getboolean("sharpen", True))
        source = path
    else:
        wx = cfg["weather"]
        if a.sample:
            with open(render_weather.SAMPLE, encoding="utf-8") as f:
                data = json.load(f)
        else:
            lat, lon = wx.get("latitude", "").strip(), wx.get("longitude", "").strip()
            if lat and lon:
                lat, lon = float(lat), float(lon)
            else:
                lat, lon, _ = render_weather.geocode(wx.get("city"), lang)
            data = render_weather.fetch(lat, lon)
        img = render_weather.render(data, wx.get("city", "").strip(), lang, orientation, a.sample)
        now = render_weather.parse(data, lang)
        _, desc = render_weather.wmo(now["code"], lang)
        source = (f'Open-Meteo{" (пример)" if a.sample else ""}: {now["now"]:%Y-%m-%d %H:%M} '
                  f'{render_weather.deg(now["temp"])} {desc}, ветер {round(now["wind"])} м/с')

    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    eink.save_png(eink.to_kindle(img, orientation, rotate), a.output)
    if a.preview:
        os.makedirs(os.path.dirname(os.path.abspath(a.preview)), exist_ok=True)
        eink.save_png(img, a.preview)
    print(f"{mode}: {source} -> {a.output}")


if __name__ == "__main__":
    main()
