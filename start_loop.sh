#!/bin/bash
# start_loop.sh - Avvia Xvfb + run_in_loop.py su Linux headless
# Uso: bash start_loop.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DISPLAY_NUM=99
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# Avvia Xvfb se non è già in esecuzione
if ! pgrep -x "Xvfb" > /dev/null; then
    echo "[start_loop] Avvio Xvfb su display :$DISPLAY_NUM"
    Xvfb :$DISPLAY_NUM -screen 0 1920x1080x16 -ac +extension GLX +render -noreset &
    sleep 2
fi

export DISPLAY=:$DISPLAY_NUM
echo "[start_loop] DISPLAY=$DISPLAY"
echo "[start_loop] Avvio run_in_loop.py..."

cd "$SCRIPT_DIR"
exec python run_in_loop.py
