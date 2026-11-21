#!/bin/sh
# Фоновый процесс: держит картинку заставки свежей.
#
# Этап 1 (по умолчанию): пока Kindle включён и есть Wi-Fi, раз в INTERVAL минут
# скачивает новую картинку в папку linkss. Когда Kindle засыпает, рисует её поверх
# экрана сна. Так на заставке всегда погода на момент засыпания (или выбранное фото).
#
# Этап 2 (RTC_WAKE=1, эксперимент): во сне будит Kindle по таймеру, обновляет и
# снова засыпает. Способ будильника на K4 уточняем через probe.sh.
. "$(dirname "$0")/common.sh"

echo $$ > "$PIDFILE"
log "start (pid $$, interval ${INTERVAL}m, rtc ${RTC_WAKE})"

# Слушатель событий сна: при уходе в заставку перерисовываем её своей картинкой.
(
	while true; do
		ev=$(lipc-wait-event com.lab126.powerd goingToScreenSaver,outOfScreenSaver 2>/dev/null)
		case "$ev" in
			goingToScreenSaver*)
				sleep 2          # даём системе нарисовать свою заставку
				draw
				log "screensaver: нарисовали"
				if [ "$RTC_WAKE" = "1" ]; then "$EXT/bin/sleep_refresh.sh" & fi
				;;
			"")
				sleep 30         # lipc-wait-event недоступен — не крутимся вхолостую
				;;
		esac
	done
) &
echo $! > "$PIDFILE.events"

# Периодическое обновление, пока Kindle бодрствует.
while true; do
	if wifi_up; then fetch; fi
	sleep $((INTERVAL * 60))
done
