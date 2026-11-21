# Настройки Dash Saver на Kindle.

# Откуда брать картинку (PNG 600x800). https:// работает через bin/ht,
# http:// — через встроенный wget.
URL="https://kiriabig.github.io/kindle-dash/dash.png"

# Как часто обновлять картинку, в минутах.
INTERVAL=30

# Экспериментально: будить Kindle во сне по таймеру, чтобы обновить погоду.
# 0 — выключено: заставка показывает картинку, свежую на момент засыпания.
# Включать после того, как probe.sh покажет, какой будильник есть на устройстве.
RTC_WAKE=0

# Куда класть картинку для хака заставок (linkss).
SS_DIR="/mnt/us/linkss/screensavers"
SS_NAME="bg_ss00.png"

LOG="/mnt/us/dashsaver.log"
