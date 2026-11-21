# Общие функции. Подключается из остальных скриптов.
EXT="$(cd "$(dirname "$0")/.." && pwd)"
. "$EXT/config.sh"
SS_FILE="$SS_DIR/$SS_NAME"
TMP_PNG="/tmp/dashsaver.png"
PIDFILE="/tmp/dashsaver.pid"

log() {
	echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"
	# не даём логу разрастись
	if [ "$(wc -c < "$LOG")" -gt 200000 ]; then
		tail -n 500 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
	fi
}

wifi_up() {
	lipc-get-prop com.lab126.wifid cmState 2>/dev/null | grep -q CONNECTED
}

wait_wifi() {  # wait_wifi <секунд>
	i=0
	while ! wifi_up && [ "$i" -lt "$1" ]; do sleep 1; i=$((i + 1)); done
	wifi_up
}

power_state() {  # active / screenSaver / ... (уточняем через probe.sh)
	lipc-get-prop com.lab126.powerd state 2>/dev/null
}

# Скачать картинку, проверить что это PNG, атомарно положить в папку заставок.
fetch() {
	rm -f "$TMP_PNG"
	case "$URL" in
		https://*) "$EXT/bin/ht" -d -q -o "$TMP_PNG" get "$URL" >/dev/null 2>&1 ;;
		*) wget -q -T 30 -O "$TMP_PNG" "$URL" ;;
	esac
	if [ ! -s "$TMP_PNG" ]; then log "fetch: пустой ответ"; return 1; fi
	if [ "$(dd if="$TMP_PNG" bs=1 skip=1 count=3 2>/dev/null)" != "PNG" ]; then
		log "fetch: это не PNG"; return 1
	fi
	mkdir -p "$SS_DIR"
	cp "$TMP_PNG" "$SS_FILE.new" && mv "$SS_FILE.new" "$SS_FILE"
	log "fetch: ok"
}

# Перерисовать экран сна нашей картинкой.
draw() {
	eips -f -g "$SS_FILE" >/dev/null 2>&1
}
