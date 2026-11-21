#!/bin/sh
. "$(dirname "$0")/common.sh"
for f in "$PIDFILE.events" "$PIDFILE"; do
	[ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null
	rm -f "$f"
done
log "stop"
eips 1 38 "Dash Saver: stopped           " >/dev/null 2>&1
