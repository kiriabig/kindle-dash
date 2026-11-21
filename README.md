# Kindle 4: заставка с погодой или фото

Kindle остаётся обычной читалкой. Когда он засыпает, на экране сна вместо стандартной заставки
показывается погода в вашем городе или выбранное фото, подготовленное под e-ink 600×800.

Статус: первая версия. Генератор картинок работает (превью в `preview/`). Часть на Kindle
написана, но ещё не проверялась на устройстве. Что проверено, а что нет, перечислено в конце.

## Как это устроено

```
 GitHub Actions (раз в 30 мин)         Kindle 4 (джейлбрейк + хак заставок)
 ┌───────────────────────────┐         ┌──────────────────────────────────────┐
 │ config.ini → dash/build.py│  HTTPS  │ Dash Saver (KUAL):                   │
 │  погода: Open-Meteo       │ ──────▶ │  пока Kindle включён, раз в 30 мин   │
 │  фото: photos/*.jpg       │ dash.png│  качает dash.png в linkss/screensavers│
 │ → GitHub Pages: dash.png  │         │  при засыпании рисует её через eips  │
 └───────────────────────────┘         └──────────────────────────────────────┘
```

Почему картинка рисуется не на самом Kindle: у Kindle 4 старый процессор, нет Python, а встроенные
`wget`/`curl` не умеют современный HTTPS. Поэтому Kindle только скачивает готовый PNG (через
маленький клиент `ht` из проекта kindle-dash) и показывает его.

## Что в папке

| Путь | Что это |
|---|---|
| `config.ini` | режим (`weather` / `photo`), ориентация, город, настройки фото |
| `dash/build.py` | собирает картинку по `config.ini` → `out/dash.png` |
| `dash/render_weather.py` | экран погоды (Open-Meteo, без ключа), русский или английский |
| `dash/convert_photo.py` | любое фото → 600×800, 16 оттенков серого с дизерингом |
| `photos/` | сюда класть фото для режима `photo` |
| `kindle/extensions/dashsaver/` | расширение KUAL для Kindle |
| `kindle/kite/dashsaver.sh` | автозапуск после перезагрузки (если стоит kite) |
| `.github/workflows/render.yml` | автосборка и публикация на GitHub Pages |
| `preview/` | как выглядят экраны |

## Запуск на Mac

```sh
python3 -m pip install pillow pillow-heif
python3 dash/build.py                 # по config.ini → out/dash.png
python3 dash/build.py --sample        # погода на тестовых данных
python3 dash/convert_photo.py ~/Pictures/photo.jpg -o out/photo.png
python3 dash/convert_photo.py ~/Pictures/photo.jpg --landscape --fit pad
```

Как готовится фото: поворот по EXIF, обрезка по центру (`crop`) или вписывание с полями (`pad`),
перевод в серый, автоконтраст, лёгкое осветление средних тонов (e-ink темнее экрана телефона),
резкость, затем дизеринг Флойда — Стейнберга до 16 уровней серого. На выходе 8-битный серый PNG
без прозрачности, размер всегда 600×800 (горизонтальная картинка поворачивается).

## Установка на Kindle (делаем вместе, по шагам)

Перед каждым шагом сделайте копию книг с Kindle. Все темы на MobileRead, ссылки ниже.

1. **Проверить модель.** Меню → Settings → Menu → Device Info: версия 4.1.4 бывает только у
   Kindle 4 без сенсора (2011–2012).
2. **Джейлбрейк** (работает на 4.0.0–4.1.4). Скопировать в корень Kindle `data.tar.gz`,
   `ENABLE_DIAGS` и папку `diagnostic_logs` из темы джейлбрейка, отключить кабель, Menu → Settings →
   Menu → Restart. В режиме диагностики: `D) Exit, Reboot or Disable Diags` → `R) Reboot System` →
   `Q) To continue`. Через ~20 секунд появится книга «You are Jailbroken».
3. **Хак заставок (linkss)** из темы NiLuJe с хаками для Kindle 2/3/4: установить через
   Settings → Menu → Update Your Kindle. Появится папка `linkss/` в корне.
4. **USBNetwork** (по желанию, из той же темы): SSH на Kindle для отладки.
5. **MKK и KUAL** (меню для запуска расширений; на K4 KUAL требует MKK).
6. **Dash Saver.** Скопировать `kindle/extensions/dashsaver` в `extensions/dashsaver` на Kindle.
   Положить в `extensions/dashsaver/bin/` файл `ht` из релиза kindle-dash. В `config.sh` вписать
   адрес картинки.
7. **Проверка.** KUAL → Dash Saver → Probe device. В корне Kindle появится `dashsaver-probe.txt`:
   по нему видно, как на этом Kindle устроены сон, будильник и Wi-Fi.
8. **Запуск.** KUAL → Dash Saver → Start. Для автозапуска после перезагрузки: kite и
   `kindle/kite/dashsaver.sh` в папку `kite/`.

## Облако: GitHub Pages

1. Создать на GitHub пустой публичный репозиторий (бесплатный Pages работает только с публичными).
2. Загрузить туда эту папку.
3. Settings → Pages → Source: **GitHub Actions**.
4. Картинка: https://kiriabig.github.io/kindle-dash/dash.png, превью для глаз:
   https://kiriabig.github.io/kindle-dash/ (адрес уже вписан в `kindle/extensions/dashsaver/config.sh`).
5. Сменить режим: отредактировать `config.ini` прямо на сайте GitHub (хоть с телефона). Фото:
   загрузить в `photos/`. Через пару минут картинка пересоберётся.

Важно знать:
- Всё на GitHub Pages публично, в том числе фото. Если фото личное, его лучше сконвертировать
  на Mac и положить на Kindle по USB в `linkss/screensavers/` (сервер для фото не нужен).
- GitHub выключает расписание в публичном репозитории после 60 дней без коммитов и присылает
  письмо: тогда нужно один раз нажать «Enable workflow».
- Запуски по расписанию на GitHub могут опаздывать на 10–20 минут. Для погоды это не страшно.

## Что проверено, а что нет

Проверено здесь:
- рендер погоды (на тестовых данных) и конвертация фото: 600×800, ровно 16 уровней серого;
- синтаксис всех shell-скриптов (`sh -n`).

Не проверено, нужно на устройстве:
- что `eips -f -g` на прошивке 4.1.4 рисует PNG поверх экрана сна;
- имена событий и свойств `powerd` (`goingToScreenSaver`, `state`) и наличие `lipc-wait-event`;
- флаги `ht` (взяты по памяти из kindle-dash, `ht -d -q -o файл get URL`);
- будильник во сне (`RTC_WAKE=1`): на K4 нет готового `rtcwake`, способ выбираем по `probe.sh`;
- открытие Open-Meteo из GitHub Actions (из этой среды сайт недоступен, проверим первым запуском).

## Ссылки

- Джейлбрейк Kindle 4: https://wiki.mobileread.com/wiki/Kindle4NTHacking
  (файлы: https://www.mobileread.com/forums/showthread.php?t=191158)
- Хаки NiLuJe для Kindle 2/3/4 (linkss, USBNetwork): https://www.mobileread.com/forums/showthread.php?t=88004
- KUAL: https://www.mobileread.com/forums/showthread.php?t=203326 · MKK: https://www.mobileread.com/forums/showthread.php?t=233932
- kite (автозапуск): https://www.mobileread.com/forums/showthread.php?t=168270
- kindle-dash (клиент `ht`): https://github.com/pascalw/kindle-dash/releases
- Похожий проект для K4: https://github.com/sibbl/hass-lovelace-kindle-4
- Погода: https://open-meteo.com (данные CC BY 4.0, подпись есть на экране)
- Шрифт Inter (SIL OFL 1.1): `fonts/LICENSE-Inter.txt`
