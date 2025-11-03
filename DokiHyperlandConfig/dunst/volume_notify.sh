#      _       _    _       _              __ _       
#     | |     | |  (_)     | |            / _(_)      
#   __| | ___ | | ___    __| | ___  _ __ | |_ _  __ _ 
#  / _` |/ _ \| |/ / |  / _` |/ _ \| '_ \|  _| |/ _` |
# | (_| | (_) |   <| | | (_| | (_) | | | | | | | (_| |
#  \__,_|\___/|_|\_\_|  \__,_|\___/|_| |_|_| |_|\__, |
#                                                __/ |
#                                               |___/ 


#!/bin/bash

# # Отримуємо рівень гучності та статус mute
# volume=$(wpctl get-volume @DEFAULT_AUDIO_SINK@ | awk '{print int($2 * 100)}')
# muted=$(wpctl get-mute @DEFAULT_AUDIO_SINK@)

# # Якщо звук вимкнено – показуємо іконку "Muted"
# if [[ "$muted" == "Muted" ]]; then
#     notify-send -u low -h string:x-dunst-stack-tag:volume -i audio-volume-muted \
#     " Muted" "<span color='#888888'>──────────</span>"  
#     exit 0
# fi

# # Визначаємо колір візуалізації
# if [[ $volume -ge 80 ]]; then
#     bar_color="#fa1955"  # Червоний при гучності >= 80%
# else
#     bar_color="#ffffff"  # Білий в іншому випадку
# fi

# # Визначаємо колір візуалізації
# if [[ $volume -le 25 ]]; then
#     bar_color="#8affb6"  # Червоний при гучності >= 80%
# else
#     bar_color="#ffffff"  # Білий в іншому випадку
# fi

# # Створюємо візуалізацію гучності у вигляді лінії
# bar=""
# filled=$((volume / 10))  # Кількість заповнених сегментів (від 0 до 10)
# empty=$((10 - filled))   # Кількість порожніх сегментів

# for ((i = 0; i < filled; i++)); do
#     bar+="█"
# done
# for ((i = 0; i < empty; i++)); do
#     bar+="─"
# done

# # Відправляємо повідомлення у dunst з кольором
# notify-send -u low -h string:x-dunst-stack-tag:volume -i audio-volume-high \
# "󰕾 Volume: $volume%" "<span color='$bar_color'>$bar</span>"

#!/usr/bin/env bash

# Отримуємо рівень гучності та статус mute
volume=$(wpctl get-volume @DEFAULT_AUDIO_SINK@ | awk '{print int($2 * 100)}')
muted=$(wpctl get-mute @DEFAULT_AUDIO_SINK@)

# Візуальна квадратна панель: 2 рядки по 5 символів
# Список символів: ░ ▒ ▓ █

# Якщо звук вимкнено – показуємо іконку "Muted"
if [[ "$muted" == "Muted" ]]; then
    notify-send -u low -h string:x-dunst-stack-tag:volume -i audio-volume-muted \
    " Muted" "<span color='#888888'>░░░░░\n░░░░░</span>"
    exit 0
fi

# Визначаємо колір залежно від рівня
if [[ $volume -le 25 ]]; then
    bar_color="#8affb6"  # зелений
elif [[ $volume -ge 80 ]]; then
    bar_color="#fa1955"  # червоний
else
    bar_color="#ffffff"  # білий
fi

# Квадратна візуалізація: 10 блоків — 2 рядки по 5
filled=$((volume / 10))
empty=$((10 - filled))
bar=""

for ((i = 0; i < filled; i++)); do
    bar+="█"
done
for ((i = 0; i < empty; i++)); do
    bar+="░"
done

# Формуємо 2 рядки по 5 символів
bar_top=${bar:0:5}
bar_bot=${bar:5:5}

# Надсилаємо повідомлення
notify-send -u low -h string:x-dunst-stack-tag:volume -i audio-volume-high \
"󰕾 Volume: $volume%" "<span color='$bar_color'>$bar_top\n$bar_bot</span>"
