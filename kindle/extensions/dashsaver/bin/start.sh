#!/bin/sh
. "$(dirname "$0")/common.sh"
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
	eips 1 38 "Dash Saver: already running   " >/dev/null 2>&1
	exit 0
fi
nohup "$EXT/bin/dashsaver.sh" >/dev/null 2>&1 &
eips 1 38 "Dash Saver: started           " >/dev/null 2>&1
