#!/bin/bash
echo "☀️ Розморожую всі процеси з ~/frozen_procs.log"
if [ -f ~/frozen_procs.log ]; then
    while read -r pid; do
        kill -CONT "$pid" 2>/dev/null && echo "🟢 Розморожено PID $pid"
    done < ~/frozen_procs.log
    rm ~/frozen_procs.log
else
    echo "Немає логів — нічого не заморожено"
fi
