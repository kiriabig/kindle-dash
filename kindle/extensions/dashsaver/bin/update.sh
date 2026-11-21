#!/bin/sh
# Скачать картинку прямо сейчас (без перерисовки экрана).
. "$(dirname "$0")/common.sh"
if fetch; then msg="updated"; else msg="FAILED, see dashsaver.log"; fi
eips 1 38 "Dash Saver: $msg          " >/dev/null 2>&1
