#!/bin/bash

# Отримуємо рівень заряду
BATTERY_LEVEL=$(cat /sys/class/power_supply/BAT*/capacity 2>/dev/null | head -n 1)

# Якщо не вдалося отримати заряд, ставимо "Unknown"
if [[ -z "$BATTERY_LEVEL" ]]; then
    BATTERY_LEVEL="Unknown"
else
    BATTERY_LEVEL="$BATTERY_LEVEL%"
fi

# Записуємо у файл
echo "Battery: $BATTERY_LEVEL" > /tmp/hyprlock_battery
