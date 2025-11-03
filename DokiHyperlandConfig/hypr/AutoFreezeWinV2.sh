#!/bin/bash

LOG=~/frozen_procs.log
declare -A last_seen
declare -A frozen

INTERVAL=1
TIMEOUT=10
WHITELIST="(vesktop|wezterm|spotify)"

echo "⏳ Відстеження активного вікна..."

while true; do
  now=$(date +%s)

  active_info=$(hyprctl activewindow -j 2>/dev/null)
  [[ -z "$active_info" || "$active_info" != *"{"* ]] && sleep $INTERVAL && continue

  active_pid=$(echo "$active_info" | jq '.pid')
  [[ -z "$active_pid" || "$active_pid" == "null" ]] && sleep $INTERVAL && continue

  echo "[✔] Активне вікно: PID $active_pid"
  last_seen[$active_pid]=$now

  if [[ "${frozen[$active_pid]}" == "1" ]]; then
    kill -CONT "$active_pid" 2>/dev/null
    if [[ $? -eq 0 ]]; then
      echo "🟢 Розморожено PID $active_pid (фокус)"
      unset frozen[$active_pid]
      sed -i "/^$active_pid\$/d" "$LOG" 2>/dev/null
    fi
  fi

  cursor_pos=$(hyprctl cursorpos -j 2>/dev/null)
  [[ -z "$cursor_pos" || "$cursor_pos" != *"{"* ]] && sleep $INTERVAL && continue
  cursor_x=$(echo "$cursor_pos" | jq '.x')
  cursor_y=$(echo "$cursor_pos" | jq '.y')

  clients_json=$(hyprctl clients -j 2>/dev/null)
  [[ -z "$clients_json" || "$clients_json" != *"["* ]] && sleep $INTERVAL && continue

  mapfile -t clients < <(echo "$clients_json" | jq -c '.[]')

  for client in "${clients[@]}"; do
    pid=$(echo "$client" | jq '.pid')
    [[ "$pid" == "null" || -z "$pid" || "$pid" == "$active_pid" ]] && continue

    cmd=$(ps -p "$pid" -o comm= 2>/dev/null)
    [[ "$cmd" =~ $WHITELIST ]] && continue

    win_x=$(echo "$client" | jq '.at[0]')
    win_y=$(echo "$client" | jq '.at[1]')
    win_w=$(echo "$client" | jq '.size[0]')
    win_h=$(echo "$client" | jq '.size[1]')

    # Якщо курсор наведено — розморозити одразу
    if (( cursor_x >= win_x && cursor_x <= win_x + win_w &&
          cursor_y >= win_y && cursor_y <= win_y + win_h )); then
      if [[ "${frozen[$pid]}" == "1" ]]; then
        kill -CONT "$pid" 2>/dev/null
        if [[ $? -eq 0 ]]; then
          echo "🟢 Розморожено PID $pid (курсор)"
          unset frozen[$pid]
          sed -i "/^$pid\$/d" "$LOG" 2>/dev/null
        fi
      fi
      last_seen[$pid]=$now
      continue
    fi

    # Заморозка після неактивності
    seen=${last_seen[$pid]}
    [[ -z "$seen" ]] && last_seen[$pid]=$now && continue

    elapsed=$((now - seen))
    if (( elapsed >= TIMEOUT )) && [[ "${frozen[$pid]}" != "1" ]]; then
      kill -STOP "$pid" 2>/dev/null
      if [[ $? -eq 0 ]]; then
        frozen[$pid]=1
        echo "🥶 Заморожено PID $pid ($elapsed сек)"
        echo "$pid" >> "$LOG"
      fi
    fi
  done

  sleep $INTERVAL
done
