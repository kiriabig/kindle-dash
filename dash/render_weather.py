"""Рисует экран с погодой для Kindle 4 по данным Open-Meteo (бесплатно, без ключа).

Пример:
    python3 dash/render_weather.py --lat 38.62 --lon -9.20 --city "Charneca da Caparica" --landscape -o out/dash.png
    python3 dash/render_weather.py --sample   # без интернета, на тестовых данных
"""

import argparse
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eink  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "fonts")
SAMPLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_weather.json")

BLACK, DARK, GRAY, LIGHT, WHITE = 0, 68, 102, 170, 255  # все кратны 17: ровно попадают в 16 уровней

# ---------------------------------------------------------------- тексты

TEXT = {
    "ru": {
        "updated": "обновлено {}",
        "sample": "ПРИМЕР ДАННЫХ",
        "source": "данные Open-Meteo",
        "feels": "ощущается", "wind": "ветер", "humidity": "влажность", "precip": "осадки",
        "maxmin": "макс {}   мин {}",
        "ms": "м/с",
        "today": "сегодня",
        "days": ["пн", "вт", "ср", "чт", "пт", "сб", "вс"],
        "days_full": ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"],
        "months": ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
                   "августа", "сентября", "октября", "ноября", "декабря"],
        "compass": ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"],
    },
    "en": {
        "updated": "updated {}",
        "sample": "SAMPLE DATA",
        "source": "data: Open-Meteo",
        "feels": "feels like", "wind": "wind", "humidity": "humidity", "precip": "rain",
        "maxmin": "high {}   low {}",
        "ms": "m/s",
        "today": "today",
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "days_full": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "months": ["January", "February", "March", "April", "May", "June", "July",
                   "August", "September", "October", "November", "December"],
        "compass": ["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
    },
}

# Коды погоды WMO -> (иконка, описание ru, описание en)
WMO = {
    0: ("clear", "Ясно", "Clear"),
    1: ("partly", "Почти ясно", "Mostly clear"),
    2: ("partly", "Переменная облачность", "Partly cloudy"),
    3: ("cloudy", "Пасмурно", "Overcast"),
    45: ("fog", "Туман", "Fog"),
    48: ("fog", "Туман с изморозью", "Rime fog"),
    51: ("drizzle", "Слабая морось", "Light drizzle"),
    53: ("drizzle", "Морось", "Drizzle"),
    55: ("drizzle", "Сильная морось", "Heavy drizzle"),
    56: ("drizzle", "Ледяная морось", "Freezing drizzle"),
    57: ("drizzle", "Ледяная морось", "Freezing drizzle"),
    61: ("rain", "Небольшой дождь", "Light rain"),
    63: ("rain", "Дождь", "Rain"),
    65: ("rain", "Сильный дождь", "Heavy rain"),
    66: ("rain", "Ледяной дождь", "Freezing rain"),
    67: ("rain", "Ледяной дождь", "Freezing rain"),
    71: ("snow", "Небольшой снег", "Light snow"),
    73: ("snow", "Снег", "Snow"),
    75: ("snow", "Сильный снег", "Heavy snow"),
    77: ("snow", "Снежная крупа", "Snow grains"),
    80: ("rain", "Небольшой ливень", "Light showers"),
    81: ("rain", "Ливень", "Showers"),
    82: ("rain", "Сильный ливень", "Violent showers"),
    85: ("snow", "Снегопад", "Snow showers"),
    86: ("snow", "Сильный снегопад", "Heavy snow showers"),
    95: ("thunder", "Гроза", "Thunderstorm"),
    96: ("thunder", "Гроза с градом", "Thunderstorm, hail"),
    99: ("thunder", "Гроза с градом", "Thunderstorm, hail"),
}


def wmo(code, lang):
    kind, ru, en = WMO.get(int(code), ("cloudy", "—", "—"))
    return kind, (ru if lang == "ru" else en)


# ---------------------------------------------------------------- данные

def fetch(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,"
                   "wind_speed_10m,wind_direction_10m,is_day",
        "hourly": "temperature_2m,weather_code,precipitation_probability,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "precipitation_probability_max,sunrise,sunset",
        "wind_speed_unit": "ms",
        "timezone": "auto",
        "forecast_days": 6,
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "kindle-weather-dash/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def geocode(name, lang="ru"):
    """Находит координаты города по названию (геокодер Open-Meteo)."""
    url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode(
        {"name": name, "count": 1, "language": lang})
    with urllib.request.urlopen(url, timeout=30) as r:
        res = json.load(r).get("results") or []
    if not res:
        raise ValueError(f"город «{name}» не найден")
    return res[0]["latitude"], res[0]["longitude"], res[0]["name"]


# ---------------------------------------------------------------- шрифты и текст

_fonts = {}


def font(style, size):
    files = {
        "display": "InterDisplay-Bold.otf",
        "display_semi": "InterDisplay-SemiBold.otf",
        "semibold": "Inter-SemiBold.otf",
        "medium": "Inter-Medium.otf",
        "regular": "Inter-Regular.otf",
    }
    key = (style, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(os.path.join(FONTS, files[style]), size)
    return _fonts[key]


def fit_font(draw, text, style, size, max_w, min_size=14):
    while size > min_size and draw.textlength(text, font=font(style, size)) > max_w:
        size -= 1
    return font(style, size)


def deg(t):
    v = int(round(t))
    return ("−" if v < 0 else "") + f"{abs(v)}°"


# ---------------------------------------------------------------- иконки

SS = 4  # рисуем в 4 раза крупнее и уменьшаем: получаются гладкие края


def _round_line(d, p1, p2, w, fill=BLACK):
    d.line([p1, p2], fill=fill, width=int(w))
    r = w / 2
    for x, y in (p1, p2):
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def _cloud(d, x, y, w, t):
    """Облако в квадрате шириной w (левый верхний угол x, y): контур толщиной t, внутри белое."""
    def shapes(inset):
        s = []
        for cx, cy, r in ((0.60, 0.42, 0.25), (0.33, 0.52, 0.17)):
            s.append(("c", x + cx * w, y + cy * w, r * w - inset))
        x0, y0, x1, y1, rad = 0.08, 0.46, 0.92, 0.76, 0.15
        s.append(("r", x + x0 * w + inset, y + y0 * w + inset,
                  x + x1 * w - inset, y + y1 * w - inset, rad * w - inset))
        return s

    for fill, inset in ((BLACK, 0), (WHITE, t)):
        for sh in shapes(inset):
            if sh[0] == "c":
                _, cx, cy, r = sh
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
            else:
                _, x0, y0, x1, y1, rad = sh
                d.rounded_rectangle([x0, y0, x1, y1], radius=max(rad, 1), fill=fill)
    # белая «сердцевина»: закрывает пятна на стыках кругов и основания
    core = [(0.33, 0.52), (0.60, 0.42), (0.77, 0.61), (0.23, 0.61)]
    d.polygon([(x + u * w, y + v * w) for u, v in core], fill=WHITE)


def _sun(d, cx, cy, r, t, skip=()):
    import math
    for i in range(8):
        if i in skip:  # лучи, которые всё равно закроет облако
            continue
        a = math.pi / 4 * i
        r1, r2 = r * 1.45, r * 1.95
        _round_line(d, (cx + r1 * math.cos(a), cy + r1 * math.sin(a)),
                    (cx + r2 * math.cos(a), cy + r2 * math.sin(a)), t)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLACK)
    d.ellipse([cx - r + t, cy - r + t, cx + r - t, cy + r - t], fill=WHITE)


def _moon(img, cx, cy, r, t):
    """Месяц контуром: внешний круг минус смещённый круг."""
    d = ImageDraw.Draw(img)
    ox, oy, r2 = r * 0.55, -r * 0.35, r * 0.85
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLACK)
    d.ellipse([cx + ox - r2, cy + oy - r2, cx + ox + r2, cy + oy + r2], fill=WHITE)
    mask = Image.new("L", img.size, 0)
    m = ImageDraw.Draw(mask)
    m.ellipse([cx - r + t, cy - r + t, cx + r - t, cy + r - t], fill=255)
    m.ellipse([cx + ox - r2 - t, cy + oy - r2 - t, cx + ox + r2 + t, cy + oy + r2 + t], fill=0)
    img.paste(WHITE, mask=mask)


def icon(kind, size, night=False):
    S = size * SS
    img = Image.new("L", (S, S), WHITE)
    d = ImageDraw.Draw(img)
    t = S * 0.055  # толщина линий

    if kind == "clear":
        if night:
            _moon(img, S * 0.5, S * 0.5, S * 0.30, t)
        else:
            _sun(d, S * 0.5, S * 0.5, S * 0.20, t)
        return img.resize((size, size), Image.Resampling.LANCZOS)

    if kind == "partly":
        if night:
            _moon(img, S * 0.64, S * 0.34, S * 0.20, t)
        else:
            _sun(d, S * 0.64, S * 0.34, S * 0.14, t, skip=(2, 3, 4))
        d = ImageDraw.Draw(img)
        _cloud(d, S * 0.02, S * 0.16, S * 0.86, t)
        return img.resize((size, size), Image.Resampling.LANCZOS)

    if kind == "cloudy":
        _cloud(d, S * 0.04, S * 0.08, S * 0.92, t)
        return img.resize((size, size), Image.Resampling.LANCZOS)

    # остальные: облако сверху, под ним осадки
    _cloud(d, S * 0.06, S * -0.04, S * 0.88, t)
    top = S * 0.74
    if kind == "rain":
        for i, x in enumerate((0.32, 0.50, 0.68)):
            x0 = S * x
            _round_line(d, (x0, top), (x0 - S * 0.07, top + S * 0.18), t)
    elif kind == "drizzle":
        for x in (0.32, 0.50, 0.68):
            for k, yy in enumerate((0.0, 0.12)):
                cx = S * x - k * S * 0.03
                cy = top + S * yy + S * 0.02
                r = t * 0.75
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLACK)
    elif kind == "snow":
        import math
        for x, yy in ((0.30, 0.06), (0.50, 0.14), (0.70, 0.06)):
            cx, cy, r = S * x, top + S * yy, S * 0.065
            for a in (0, 60, 120):
                ang = math.radians(a + 90)
                _round_line(d, (cx - r * math.cos(ang), cy - r * math.sin(ang)),
                            (cx + r * math.cos(ang), cy + r * math.sin(ang)), t * 0.7)
    elif kind == "thunder":
        bolt = [(0.54, 0.60), (0.38, 0.84), (0.50, 0.84), (0.44, 1.0), (0.64, 0.74),
                (0.52, 0.74), (0.60, 0.60)]
        d.polygon([(S * x, S * y - S * 0.02) for x, y in bolt], fill=BLACK)
    elif kind == "fog":
        for yy, x0, x1 in ((0.0, 0.18, 0.82), (0.13, 0.26, 0.74)):
            _round_line(d, (S * x0, top + S * yy + S * 0.04), (S * x1, top + S * yy + S * 0.04), t)
    return img.resize((size, size), Image.Resampling.LANCZOS)


def drop(size):
    """Капля для вероятности осадков."""
    S = size * SS
    img = Image.new("L", (S, S), WHITE)
    d = ImageDraw.Draw(img)
    r = S * 0.30
    cx, cy = S * 0.5, S * 0.62
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GRAY)
    d.polygon([(cx - r * 0.93, cy - r * 0.35), (cx, S * 0.06), (cx + r * 0.93, cy - r * 0.35)], fill=GRAY)
    return img.resize((size, size), Image.Resampling.LANCZOS)


# ---------------------------------------------------------------- разбор прогноза

def parse(data, lang):
    T = TEXT[lang]
    cur = data["current"]
    now = dt.datetime.fromisoformat(cur["time"])
    h, dd = data["hourly"], data["daily"]

    hours = [dt.datetime.fromisoformat(x) for x in h["time"]]
    start = next(i for i, x in enumerate(hours) if x > now)
    hourly = []
    for i in range(start, len(hours), 3):
        hourly.append({
            "time": hours[i].strftime("%H:%M"),
            "temp": h["temperature_2m"][i],
            "code": h["weather_code"][i],
            "night": not h["is_day"][i],
            "precip": h["precipitation_probability"][i] or 0,
        })

    days = []
    for i, day in enumerate(dd["time"]):
        d = dt.date.fromisoformat(day)
        days.append({
            "date": d,
            "label": T["today"] if d == now.date() else f'{T["days"][d.weekday()]}, {d.day}',
            "code": dd["weather_code"][i],
            "max": dd["temperature_2m_max"][i],
            "min": dd["temperature_2m_min"][i],
            "precip": dd["precipitation_probability_max"][i] or 0,
        })
    today = next((x for x in days if x["date"] == now.date()), days[0])
    future = [x for x in days if x["date"] > now.date()]

    wd = cur["wind_direction_10m"]
    return {
        "now": now,
        "temp": cur["temperature_2m"],
        "feels": cur["apparent_temperature"],
        "humidity": cur["relative_humidity_2m"],
        "wind": cur["wind_speed_10m"],
        "wind_dir": T["compass"][int((wd + 22.5) // 45) % 8],
        "code": cur["weather_code"],
        "night": not cur["is_day"],
        "today": today,
        "hourly": hourly,
        "days": future,
    }


def date_line(now, lang):
    T = TEXT[lang]
    if lang == "ru":
        return f'{T["days_full"][now.weekday()]}, {now.day} {T["months"][now.month - 1]}'
    return f'{T["days_full"][now.weekday()]}, {T["months"][now.month - 1]} {now.day}'


# ---------------------------------------------------------------- отрисовка

def _header(img, d, w, city, wx, lang, sample, m):
    T = TEXT[lang]
    right = T["sample"] if sample else T["updated"].format(wx["now"].strftime("%H:%M"))
    d.text((w - m, 36), right, font=font("medium", 19), fill=BLACK if sample else DARK, anchor="ra")
    d.text((w - m, 64), T["source"], font=font("regular", 15), fill=GRAY, anchor="ra")
    city_w = w - 2 * m - max(d.textlength(right, font=font("medium", 19)), 150) - 16
    d.text((m, 30), city, font=fit_font(d, city, "semibold", 38, city_w), fill=BLACK, anchor="la")
    d.text((m, 80), date_line(wx["now"], lang), font=font("regular", 22), fill=DARK, anchor="la")


def _details(d, x, y, col_w, items, cols, row_h=66):
    for i, (label, value) in enumerate(items):
        cx = x + (i % cols) * col_w
        cy = y + (i // cols) * row_h
        d.text((cx, cy), label, font=font("regular", 18), fill=GRAY, anchor="la")
        d.text((cx, cy + 24), value, font=font("semibold", 26), fill=BLACK, anchor="la")


def _hourly(img, d, x, y, slot_w, slots, icon_size, gap=4):
    for i, s in enumerate(slots):
        cx = x + slot_w * i + slot_w / 2
        d.text((cx, y), s["time"], font=font("regular", 19), fill=DARK, anchor="ma")
        kind, _ = wmo(s["code"], "ru")
        img.paste(icon(kind, icon_size, s["night"]), (int(cx - icon_size / 2), y + 28))
        ty = y + 28 + icon_size + gap
        d.text((cx, ty), deg(s["temp"]), font=font("semibold", 26), fill=BLACK, anchor="ma")
        if s["precip"] >= 10:
            d.text((cx, ty + 31), f'{s["precip"]}%', font=font("regular", 17), fill=GRAY, anchor="ma")


def _daily(img, d, x0, x1, y, row_h, days, icon_size):
    for i, day in enumerate(days):
        cy = y + row_h * i + row_h / 2
        d.text((x0, cy), day["label"], font=font("medium", 23), fill=BLACK, anchor="lm")
        ix = x0 + 92
        kind, _ = wmo(day["code"], "ru")
        img.paste(icon(kind, icon_size), (int(ix), int(cy - icon_size / 2)))
        if day["precip"] >= 10:
            px = ix + icon_size + 14
            img.paste(drop(18), (int(px), int(cy - 10)))
            d.text((px + 20, cy), f'{day["precip"]}%', font=font("regular", 19), fill=GRAY, anchor="lm")
        d.text((x1, cy), deg(day["min"]), font=font("regular", 23), fill=GRAY, anchor="rm")
        d.text((x1 - 58, cy), deg(day["max"]), font=font("semibold", 23), fill=BLACK, anchor="rm")


def render(data, city, lang="ru", orientation="portrait", sample=False):
    T = TEXT[lang]
    wx = parse(data, lang)
    w, h = eink.target_size(orientation)
    img = Image.new("L", (w, h), WHITE)
    d = ImageDraw.Draw(img)
    m = 36 if orientation == "portrait" else 32
    kind, desc = wmo(wx["code"], lang)
    today = wx["today"]
    details = [
        (T["feels"], deg(wx["feels"])),
        (T["wind"], f'{round(wx["wind"])} {T["ms"]} {wx["wind_dir"]}'),
        (T["humidity"], f'{round(wx["humidity"])}%'),
        (T["precip"], f'{today["precip"]}%'),
    ]

    _header(img, d, w, city, wx, lang, sample, m)
    d.line([(m, 122), (w - m, 122)], fill=LIGHT, width=2)

    if orientation == "portrait":
        isz = 196
        img.paste(icon(kind, isz, wx["night"]), (m - 12, 138))
        tx = m + isz + 6
        d.text((tx, 300), deg(wx["temp"]), font=font("display", 132), fill=BLACK, anchor="ls")
        d.text((tx + 4, 318), desc, font=fit_font(d, desc, "medium", 26, w - m - tx), fill=BLACK, anchor="la")
        d.text((tx + 4, 354), T["maxmin"].format(deg(today["max"]), deg(today["min"])),
               font=font("regular", 21), fill=DARK, anchor="la")
        _details(d, m, 402, (w - 2 * m) / 4, details, 4)
        d.line([(m, 484), (w - m, 484)], fill=LIGHT, width=2)
        _hourly(img, d, m - 8, 500, (w - 2 * m + 16) / 6, wx["hourly"][:6], 54)
        d.line([(m, 664), (w - m, 664)], fill=LIGHT, width=2)
        _daily(img, d, m, w - m, 672, 31, wx["days"][:4], 30)
    else:
        isz = 150
        img.paste(icon(kind, isz, wx["night"]), (m - 10, 132))
        tx = m + isz + 8
        d.text((tx, 242), deg(wx["temp"]), font=font("display", 110), fill=BLACK, anchor="ls")
        colx = 420
        d.text((tx + 2, 258), desc, font=fit_font(d, desc, "medium", 24, colx - tx - 10), fill=BLACK, anchor="la")
        d.text((tx + 2, 290), T["maxmin"].format(deg(today["max"]), deg(today["min"])),
               font=font("regular", 20), fill=DARK, anchor="la")
        _details(d, m, 324, 194, details, 2, row_h=60)
        d.line([(colx + 16, 140), (colx + 16, 436)], fill=LIGHT, width=2)
        _daily(img, d, colx + 40, w - m, 132, 62, wx["days"][:5], 36)
        d.line([(m, 452), (w - m, 452)], fill=LIGHT, width=2)
        _hourly(img, d, m - 6, 462, (w - 2 * m + 12) / 8, wx["hourly"][:8], 40, gap=2)

    return eink.quantize(img, dither=False)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--city", default="Charneca da Caparica")
    p.add_argument("--lat", type=float, default=38.62)
    p.add_argument("--lon", type=float, default=-9.20)
    p.add_argument("--lang", choices=("ru", "en"), default="ru")
    p.add_argument("--landscape", action="store_true")
    p.add_argument("--rotate", type=int, default=90, choices=(90, 270))
    p.add_argument("--sample", action="store_true", help="тестовые данные вместо запроса в интернет")
    p.add_argument("-o", "--output", default="out/dash.png")
    a = p.parse_args()

    if a.sample:
        with open(SAMPLE, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = fetch(a.lat, a.lon)
    orientation = "landscape" if a.landscape else "portrait"
    img = render(data, a.city, a.lang, orientation, a.sample)
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    eink.save_png(eink.to_kindle(img, orientation, a.rotate), a.output)
    print(a.output)


if __name__ == "__main__":
    main()
