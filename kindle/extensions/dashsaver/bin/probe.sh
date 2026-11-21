#!/bin/sh
# Собирает сведения об устройстве в /mnt/us/dashsaver-probe.txt.
# Ничего не меняет. Файл потом можно скопировать с Kindle по USB.
. "$(dirname "$0")/common.sh"
OUT=/mnt/us/dashsaver-probe.txt
{
	echo "== date";        date
	echo "== version";     cat /etc/prettyversion.txt 2>/dev/null; uname -a
	echo "== serial";      cat /proc/usid 2>/dev/null | cut -c1-6
	echo "== tools";       for t in lipc-get-prop lipc-set-prop lipc-wait-event lipc-probe eips wget curl rtcwake; do printf '%s: ' "$t"; which "$t" || echo no; done
	echo "== powerd";      lipc-probe -v com.lab126.powerd 2>&1
	echo "== powerd state"; lipc-get-prop com.lab126.powerd state 2>&1; lipc-get-prop com.lab126.powerd status 2>&1
	echo "== wifid";       lipc-get-prop com.lab126.wifid cmState 2>&1
	echo "== rtc";         ls -l /sys/class/rtc/ /sys/class/rtc/rtc0/ /sys/devices/platform/mxc_rtc.0/ 2>&1
	echo "== power";       cat /sys/power/state 2>&1
	echo "== linkss";      ls -la /mnt/us/linkss /mnt/us/linkss/screensavers 2>&1 | head -30
	echo "== blanket";     mount | grep -i -e blanket -e linkss
	echo "== ht";          ls -l "$EXT/bin/ht" 2>&1
	echo "== fetch test";  if fetch; then echo ok; ls -l "$SS_FILE"; else echo FAILED; fi
	echo "== log tail";    tail -n 20 "$LOG" 2>/dev/null
} > "$OUT" 2>&1
eips 1 38 "Dash Saver: probe saved to dashsaver-probe.txt" >/dev/null 2>&1
