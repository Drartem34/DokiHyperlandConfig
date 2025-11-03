#!/bin/bash
hyprctl clients -j | jq -r '.[] | "windowrulev2 = move \(.at[0]) \(.at[1]), class:\(.class)"' > ~/.config/hypr/saved_positions.conf
