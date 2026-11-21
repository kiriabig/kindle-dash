#!/bin/sh
# ЭКСПЕРИМЕНТ (RTC_WAKE=1): обновления во время сна.
# Будильник ставится одним из способов ниже; какой работает на K4 4.1.4,
# покажет probe.sh. Пока это черновик, его надо проверить на устройстве.
. "$(dirname "$0")/common.sh"

set_alarm() {  # set_alarm <секунд>
	if lipc-get-prop com.lab126.powerd rtcWakeup >/dev/null 2>&1; then
		lipc-set-prop -i com.lab126.powerd rtcWakeup "$1" && return 0
	fi
	if [ -w /sys/devices/platform/mxc_rtc.0/wakeup_enable ]; then
		echo "$1" > /sys/devices/platform/mxc_rtc.0/wakeup_enable && return 0
	fi
	if [ -w /sys/class/rtc/rtc0/wakealarm ]; then
		echo 0 > /sys/class/rtc/rtc0/wakealarm
		echo "+$1" > /sys/class/rtc/rtc0/wakealarm && return 0
	fi
	log "rtc: не нашли способ поставить будильник"
	return 1
}

while power_state | grep -qi screensaver; do
	set_alarm $((INTERVAL * 60)) || exit 1
	log "rtc: будильник через ${INTERVAL}m"
	# ждём, пока устройство уснёт и проснётся по будильнику
	lipc-wait-event com.lab126.powerd resuming >/dev/null 2>&1 || sleep $((INTERVAL * 60))
	power_state | grep -qi screensaver || break   # проснулись от кнопки — выходим
	lipc-set-prop com.lab126.wifid enable 1 2>/dev/null
	if wait_wifi 45 && fetch; then draw; log "rtc: обновили во сне"; fi
done
