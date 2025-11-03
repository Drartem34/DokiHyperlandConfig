#      _       _    _       _              __ _       
#     | |     | |  (_)     | |            / _(_)      
#   __| | ___ | | ___    __| | ___  _ __ | |_ _  __ _ 
#  / _` |/ _ \| |/ / |  / _` |/ _ \| '_ \|  _| |/ _` |
# | (_| | (_) |   <| | | (_| | (_) | | | | | | | (_| |
#  \__,_|\___/|_|\_\_|  \__,_|\___/|_| |_|_| |_|\__, |
#                                                __/ |
#                                               |___/ 


# # Затримка 0.1 сек, щоб оновилась мета-інформація
# sleep 1

# # Отримуємо статус, назву треку та обкладинку
# player_status=$(playerctl status 2>/dev/null)
# track_name=$(playerctl metadata title 2>/dev/null)
# album_art=$(playerctl metadata mpris:artUrl 2>/dev/null)

# # Якщо немає треку — пишемо заглушку
# if [[ -z "$track_name" ]]; then
#     track_name="No track playing"
# fi

# # Вибір іконки для статусу
# if [[ "$player_status" == " Playing" ]]; then
#     music_icon="■"  # Плей 
# elif [[ "$player_status" == " Paused" ]]; then
#     music_icon=""  # Пауза 
# else
#     music_icon="󰝚"  # Немає треку 󰝚
# fi

# # Якщо немає картинки альбому — використовуємо стандартну
# if [[ -z "$album_art" ]]; then
#     album_art="/usr/share/icons/Papirus/64x64/categories/multimedia.svg"
# fi

# # Оновлюємо сповіщення з картинкою
# notify-send -u low -h string:x-dunst-stack-tag:music -i "$album_art" \
# "$music_icon Now playing" "$track_name"#!/usr/bin/env bash

#!/usr/bin/env bash

#!/usr/bin/env bash

# 1. Отримуємо гучність та статус
volume=$(wpctl get-volume @DEFAULT_AUDIO_SINK@ | awk '{print int($2 * 100)}')
muted=$(wpctl get-mute @DEFAULT_AUDIO_SINK@)
timestamp=$(date +"%H:%M:%S")

# 2. Отримуємо трек (якщо доступно)
if command -v playerctl &>/dev/null; then
    now_playing=$(playerctl metadata title 2>/dev/null | xargs)
    [[ -z "$now_playing" ]] && now_playing="Nothing playing"
else
    now_playing="playerctl not found"
fi

# 3. Динамічний вибір іконки
if [[ "$muted" == "Muted" ]]; then
    icon="audio-volume-muted"
    bar="░░░░░\n░░░░░"
    notify-send -u low -h string:x-dunst-stack-tag:volume -i $icon \
    " Muted [$timestamp]" "<span color='#888888'>$bar\n🎵 $now_playing</span>"
    exit 0
elif [[ $volume -le 25 ]]; then
    icon="audio-volume-low"
elif [[ $volume -le 70 ]]; then
    icon="audio-volume-medium"
else
    icon="audio-volume-high"
fi

# 4. Колір залежно від рівня (градієнт)
if [[ $volume -le 25 ]]; then
    bar_color="#8affb6"
elif [[ $volume -le 50 ]]; then
    bar_color="#aadfff"
elif [[ $volume -le 75 ]]; then
    bar_color="#ffe98a"
else
    bar_color="#fa1955"
fi

# 5. Створюємо квадратну панель
filled=$((volume / 10))
empty=$((10 - filled))
bar=""

for ((i = 0; i < filled; i++)); do
    bar+="█"
done
for ((i = 0; i < empty; i++)); do
    bar+="░"
done

bar_top=${bar:0:5}
bar_bot=${bar:5:5}

# 6. Сповіщення
notify-send -u low -h string:x-dunst-stack-tag:volume -i $icon \
"󰕾 Volume: $volume% [$timestamp]" "<span color='$bar_color'>$bar_top\n$bar_bot\n🎵 $now_playing</span>"
