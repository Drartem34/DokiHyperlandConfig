import sys
import os
import json
import subprocess
import gi
import switcher
sys.path.append(os.path.expanduser("~/.config/ignis"))
import dock
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk
from ignis import widgets, utils
from ignis.app import IgnisApp
from ignis.services.audio import AudioService
from ignis.services.mpris import MprisService

app = IgnisApp.get_initialized()
audio = AudioService.get_default()
mpris = MprisService.get_default()

app.apply_css(os.path.expanduser("~/.config/ignis/style.css"))

# --- HELPER FUNCTIONS ---
def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    except:
        return ""

def get_wifi_status():
    ssid = run_cmd("nmcli -t -f ACTIVE,SSID dev wifi | grep '^yes' | cut -d: -f2")
    state = run_cmd("nmcli -t -f STATE general")
    return ssid, state == "connected"

def get_bt_status():
    out = run_cmd("bluetoothctl show | grep 'Powered: yes'")
    return bool(out)

# --- CUSTOM CLICKABLE BOX (ВИПРАВЛЕНО ЦЕНТРУВАННЯ) ---
def ClickableBox(child, on_click, css_classes=[], spacing=0, centered=False):
    # Якщо потрібно центрувати вміст (для кнопок)
    if centered and child:
        child.set_halign("center")
        child.set_valign("center")
        child.set_hexpand(True)
        child.set_vexpand(True)

    box = widgets.Box(
        child=[child] if child else [],
        css_classes=css_classes,
        spacing=spacing,
    )
    
    gesture = Gtk.GestureClick()
    gesture.connect("released", lambda x, n, a, b: on_click(box))
    box.add_controller(gesture)
    
    def on_hover(w, event):
        try: w.set_cursor(Gdk.Cursor.new_from_name("pointer", None))
        except: pass
    
    motion = Gtk.EventControllerMotion()
    motion.connect("enter", on_hover)
    box.add_controller(motion)

    return box

# --- БЛОК ---
def Block(child, is_active=False, is_wide=False, css_class=None, on_click=None):
    styles = ["block"]
    styles.append("active" if is_active else "dark")
    styles.append("wide" if is_wide else "std")
    if css_class: styles.append(css_class)

    box = widgets.Box(
        child=[child] if child else [],
        spacing=10,
        halign="start" if is_wide else "center",
        valign="center",
        hexpand=True,
        css_classes=styles,
    )

    if on_click:
        gesture = Gtk.GestureClick()
        gesture.connect("released", lambda x, n, a, b: on_click(box))
        box.add_controller(gesture)
        motion = Gtk.EventControllerMotion()
        motion.connect("enter", lambda w, e: w.set_cursor(Gdk.Cursor.new_from_name("pointer", None)))
        box.add_controller(motion)

    return box

# --- LIST ITEM ---
def ListItem(icon, label, is_connected, on_click):
    # Тут centered=False, бо текст має бути зліва
    return ClickableBox(
        child=widgets.Box(
            spacing=10,
            child=[
                widgets.Label(label=icon, css_classes=["list-icon"]),
                widgets.Label(label=label, css_classes=["list-label"], ellipsize="end", halign="start", hexpand=True),
                widgets.Label(label="✔" if is_connected else "", css_classes=["list-status"])
            ]
        ),
        on_click=lambda x: on_click(),
        css_classes=["list-item", "list-item-active" if is_connected else "list-item-normal"]
    )

# --- WI-FI ---
def WifiWidget():
    list_revealer = widgets.Revealer(transition_type="slide_down")
    list_box = widgets.Box(vertical=True, spacing=5, css_classes=["list-container"])
    
    icon_label = widgets.Label(label="", css_classes=["b-icon"])
    status_label = widgets.Label(label="Checking...", halign="start", css_classes=["card-status"], ellipsize="end")

    def refresh_wifi_list():
        child = list_box.get_first_child()
        while child: list_box.remove(child); child = list_box.get_first_child()
        list_box.append(widgets.Label(label="Scanning...", css_classes=["b-subtext"]))
        try:
            os.system("nmcli dev wifi rescan") 
            raw = run_cmd("nmcli -t -f SSID,IN-USE,SIGNAL dev wifi list")
            child = list_box.get_first_child()
            while child: list_box.remove(child); child = list_box.get_first_child()
            
            lines = raw.split('\n'); unique_ssids = set(); count = 0
            for line in lines:
                if not line: continue
                parts = line.split(':')
                if len(parts) < 2: continue
                ssid = parts[0]; is_active = parts[1] == "yes"
                if not ssid or ssid in unique_ssids: continue
                unique_ssids.add(ssid)
                connect_cmd = f"nmcli dev wifi connect '{ssid}'"
                list_box.append(ListItem("", ssid, is_active, lambda c=connect_cmd: os.system(c)))
                count += 1
                if count > 15: break
            if count == 0: list_box.append(widgets.Label(label="No networks", css_classes=["b-subtext"]))
        except: list_box.append(widgets.Label(label="Error", css_classes=["b-subtext"]))

    def toggle_list(widget):
        is_open = list_revealer.get_reveal_child()
        if not is_open: refresh_wifi_list()
        list_revealer.set_reveal_child(not is_open)

    def poll_status(widget):
        ssid, connected = get_wifi_status()
        if not ssid:
            radio = run_cmd("nmcli radio wifi")
            if radio == "disabled":
                status_label.set_label("Disabled"); icon_label.set_label("睊"); icon_label.add_css_class("dim-icon"); icon_label.remove_css_class("accent-icon")
            else:
                status_label.set_label("Disconnected"); icon_label.set_label(""); icon_label.add_css_class("dim-icon"); icon_label.remove_css_class("accent-icon")
        else:
            status_label.set_label(ssid); icon_label.set_label(""); icon_label.add_css_class("accent-icon"); icon_label.remove_css_class("dim-icon")

    utils.Poll(2000, lambda x: poll_status(None))

    # Кнопка живлення (З ЦЕНТРУВАННЯМ)
    power_btn = ClickableBox(
        child=widgets.Label(label=""),
        css_classes=["power-btn"],
        on_click=lambda x: os.system("nmcli radio wifi off" if run_cmd("nmcli radio wifi") == "enabled" else "nmcli radio wifi on"),
        centered=True # <--- Центрує іконку
    )

    header_left = ClickableBox(
        child=widgets.Box(spacing=12, child=[icon_label, widgets.Box(vertical=True, valign="center", child=[widgets.Label(label="Wi-Fi", halign="start", css_classes=["card-title"]), status_label])]),
        on_click=toggle_list,
        css_classes=["header-left"]
    )
    
    header = widgets.Box(spacing=0, child=[header_left, widgets.Box(hexpand=True), power_btn])
    scroll = widgets.Scroll(height_request=250, child=list_box); list_revealer.set_child(scroll)
    return widgets.Box(vertical=True, css_classes=["block", "dark", "wide"], child=[widgets.Box(css_classes=["header-padding"], child=[header]), list_revealer])

# --- BLUETOOTH ---
def BluetoothWidget():
    list_revealer = widgets.Revealer(transition_type="slide_down")
    list_box = widgets.Box(vertical=True, spacing=5, css_classes=["list-container"])
    icon_label = widgets.Label(label="", css_classes=["b-icon"])
    status_label = widgets.Label(label="Checking...", halign="start", css_classes=["card-status"])

    def refresh_bt_list():
        child = list_box.get_first_child()
        while child: list_box.remove(child); child = list_box.get_first_child()
        try:
            raw = run_cmd("bluetoothctl devices"); lines = raw.split('\n'); count = 0
            for line in lines:
                if not line: continue
                parts = line.split(' ', 2)
                if len(parts) < 3: continue
                mac = parts[1]; name = parts[2]
                info = run_cmd(f"bluetoothctl info {mac}"); is_connected = "Connected: yes" in info
                cmd = f"bluetoothctl disconnect {mac}" if is_connected else f"bluetoothctl connect {mac}"
                list_box.append(ListItem("", name, is_connected, lambda c=cmd: os.system(c)))
                count += 1
            if count == 0: list_box.append(widgets.Label(label="No devices", css_classes=["b-subtext"]))
        except: list_box.append(widgets.Label(label="Error", css_classes=["b-subtext"]))

    def toggle_list(widget):
        is_open = list_revealer.get_reveal_child()
        if not is_open: refresh_bt_list()
        list_revealer.set_reveal_child(not is_open)

    def poll_status(widget):
        is_on = get_bt_status()
        status_label.set_label("On" if is_on else "Off"); icon_label.set_label("" if is_on else "")
        if is_on: icon_label.add_css_class("accent-icon"); icon_label.remove_css_class("dim-icon")
        else: icon_label.add_css_class("dim-icon"); icon_label.remove_css_class("accent-icon")

    utils.Poll(2000, lambda x: poll_status(None))

    # Кнопка живлення (З ЦЕНТРУВАННЯМ)
    power_btn = ClickableBox(
        child=widgets.Label(label=""),
        css_classes=["power-btn"],
        on_click=lambda x: os.system("bluetoothctl power off" if get_bt_status() else "bluetoothctl power on"),
        centered=True # <--- Центрує іконку
    )

    header_left = ClickableBox(
        child=widgets.Box(spacing=12, child=[icon_label, widgets.Box(vertical=True, valign="center", child=[widgets.Label(label="Bluetooth", halign="start", css_classes=["card-title"]), status_label])]),
        on_click=toggle_list,
        css_classes=["header-left"]
    )

    header = widgets.Box(spacing=0, child=[header_left, widgets.Box(hexpand=True), power_btn])
    scroll = widgets.Scroll(height_request=250, child=list_box); list_revealer.set_child(scroll)
    return widgets.Box(vertical=True, css_classes=["block", "dark", "wide"], child=[widgets.Box(css_classes=["header-padding"], child=[header]), list_revealer])

# --- МУЗИКА ---
def MusicWidget():
    art_label = widgets.Label(label="", css_classes=["music-fallback-icon"])
    art_box = widgets.Box(child=[art_label], css_classes=["music-art-icon"])
    
    title_label = widgets.Label(label="No Media Playing", halign="start", ellipsize="end", css_classes=["music-title"])
    artist_label = widgets.Label(label="", halign="start", ellipsize="end", css_classes=["music-artist"])
    play_pause_icon = widgets.Label(label="", css_classes=["player-icon"])

    def get_priority_player():
        try:
            players_raw = run_cmd("playerctl -l")
            if not players_raw: return None
            players = players_raw.splitlines()
            for p in players:
                status = run_cmd(f"playerctl -p {p} status").strip().lower()
                if status == "playing": return p
            return players[0]
        except: return None

    def send_cmd(action):
        target = get_priority_player()
        if target: os.system(f"playerctl -p {target} {action}")

    # Кнопки (З ЦЕНТРУВАННЯМ)
    btn_prev = ClickableBox(
        child=widgets.Label(label=""), 
        on_click=lambda x: send_cmd("previous"), 
        css_classes=["control-btn"],
        centered=True # <--- Центрує
    )
    
    btn_play = ClickableBox(
        child=play_pause_icon, 
        on_click=lambda x: send_cmd("play-pause"), 
        css_classes=["play-btn"], 
        spacing=0,
        centered=True # <--- Центрує
    )
    
    btn_next = ClickableBox(
        child=widgets.Label(label=""), 
        on_click=lambda x: send_cmd("next"), 
        css_classes=["control-btn"],
        centered=True # <--- Центрує
    )

    def update_music(widget):
        try:
            target = get_priority_player()
            if not target:
                title_label.set_label("No Media Playing"); artist_label.set_label("")
                play_pause_icon.set_label(""); art_box.set_style(""); art_label.set_visible(True)
                return

            status = run_cmd(f"playerctl -p {target} status").strip().lower()
            metadata = run_cmd(f"playerctl -p {target} metadata --format '{{{{title}}}};{{{{artist}}}};{{{{mpris:artUrl}}}}'")
            
            if metadata:
                parts = metadata.split(";")
                if len(parts) >= 3:
                    title = parts[0] if parts[0] else "Unknown"
                    artist = parts[1] if parts[1] else "Unknown"
                    art_url = parts[2]

                    if title_label.label != title: title_label.set_label(title)
                    if artist_label.label != artist: artist_label.set_label(artist)
                    
                    if art_url:
                        if "file://" in art_url:
                            path = art_url.replace("file://", "")
                            art_box.set_style(f"background-image: url('file://{path}'); background-size: cover; background-position: center; padding: 0;")
                            art_label.set_visible(False)
                        elif "http" in art_url:
                            art_box.set_style(f"background-image: url('{art_url}'); background-size: cover; background-position: center; padding: 0;")
                            art_label.set_visible(False)
                        else:
                            art_box.set_style(""); art_label.set_visible(True)
                    else:
                        art_box.set_style(""); art_label.set_visible(True)

            if "playing" in status:
                if play_pause_icon.label != "": play_pause_icon.set_label("")
            else:
                if play_pause_icon.label != "": play_pause_icon.set_label("")
        except: pass

    utils.Poll(1000, lambda x: update_music(None))
    update_music(None)

    return widgets.Box(
        css_classes=["music-box"],
        vertical=True,
        child=[
            widgets.Box(spacing=15, child=[
                art_box,
                widgets.Box(vertical=True, valign="center", hexpand=True, child=[title_label, artist_label])
            ]),
            widgets.Box(height_request=15),
            widgets.Box(halign="center", spacing=20, child=[btn_prev, btn_play, btn_next])
        ]
    )

# --- ЗВУК/МІКРО ---
def VolumeControl():
    scale = widgets.Scale(min=0, max=100, step=1, hexpand=True, css_classes=["b-slider"])
    def on_change(widget): os.system(f"pamixer --set-volume {int(widget.value)}")
    def update(widget):
        try:
            vol = run_cmd("pamixer --get-volume")
            if vol.isdigit() and abs(int(widget.value) - int(vol)) > 1: widget.set_value(int(vol))
        except: pass
    scale.connect("change-value", lambda x, y: on_change(x)); utils.Poll(1000, lambda x: update(scale)); update(scale)
    return widgets.Box(css_classes=["block", "dark", "wide"], spacing=10, child=[widgets.Label(label="", css_classes=["b-icon"]), scale])

def MicrophoneControl():
    scale = widgets.Scale(min=0, max=100, step=1, hexpand=True, css_classes=["b-slider"])
    def on_change(widget): os.system(f"pamixer --default-source --set-volume {int(widget.value)}")
    def update(widget):
        try:
            vol = run_cmd("pamixer --default-source --get-volume")
            if vol.isdigit() and abs(int(widget.value) - int(vol)) > 1: widget.set_value(int(vol))
        except: pass
    scale.connect("change-value", lambda x, y: on_change(x)); utils.Poll(1000, lambda x: update(scale)); update(scale)
    return widgets.Box(css_classes=["block", "dark", "wide"], spacing=10, child=[widgets.Label(label="", css_classes=["b-icon"]), scale])

    

# --- СПОВІЩЕННЯ ---
HIDDEN_NOTIF_IDS = set()
def NotificationItem(appname, summary, body, icon_data, item_id, on_dismiss):
    def get_val(key):
        val = icon_data.get(key)
        if isinstance(val, dict): return val.get("data", "")
        return val if val else ""
    raw_path = get_val("icon_path"); raw_name = get_val("app_icon")
    image_source = "dialog-information"
    if raw_path and "/" in raw_path:
        clean_path = raw_path.replace("file://", "")
        if os.path.exists(clean_path): image_source = clean_path
    elif raw_name: image_source = raw_name
    elif appname: image_source = appname.lower().split()[0]
    
    if image_source in ["notify-send", "dunst", "notification-daemon"]: image_source = "dialog-information"
    if "telegram" in image_source: image_source = "telegram"
    if "code" in image_source: image_source = "code"
    if "firefox" in image_source: image_source = "firefox"

    box = widgets.Box(css_classes=["notif-item"], vertical=True, child=[
        widgets.Box(spacing=12, child=[
            widgets.Icon(image=image_source, pixel_size=32, css_classes=["notif-icon-img"]),
            widgets.Box(vertical=True, valign="center", hexpand=True, child=[
                widgets.Label(label=appname, css_classes=["notif-appname"], halign="start", ellipsize="end"),
                widgets.Label(label=summary, css_classes=["notif-summary"], halign="start", ellipsize="end", max_width_chars=30)])]),
        widgets.Box(height_request=6),
        widgets.Label(label=body, css_classes=["notif-body"], halign="start", wrap=True, max_width_chars=45)
    ])
    def on_click_handler(gesture, n_press, x, y):
        if gesture.get_current_button() == 2: on_dismiss(box, item_id)
    gesture = Gtk.GestureClick(); gesture.set_button(0); gesture.connect("released", on_click_handler); box.add_controller(gesture)
    return box

def NotificationWidget():
    notif_list = widgets.Box(vertical=True, spacing=10)
    BLACKLIST = ["notify-send", "volume", "brightness", "backlight", "microphone"]
    def dismiss_item(widget, notif_id):
        notif_list.remove(widget); 
        if notif_id: HIDDEN_NOTIF_IDS.add(notif_id)
    def refresh_notifications():
        child = notif_list.get_first_child()
        while child: notif_list.remove(child); child = notif_list.get_first_child()
        try:
            raw_json = run_cmd("dunstctl history"); 
            if not raw_json: notif_list.append(widgets.Label(label="No history", css_classes=["b-subtext"])); return
            data = json.loads(raw_json); history = data.get("data", [[]])[0]; count = 0
            for item in history:
                if count >= 30: break
                item_id = item.get("id", {}).get("data")
                if item_id in HIDDEN_NOTIF_IDS: continue
                appname = item.get("appname", {}).get("data", "System")
                summary = item.get("summary", {}).get("data", "")
                body = item.get("body", {}).get("data", "")
                check_str = (appname + " " + summary).lower()
                is_spam = False
                for bad_word in BLACKLIST:
                    if bad_word in check_str: is_spam = True; break
                if is_spam: continue
                notif_list.append(NotificationItem(appname, summary, body, item, item_id, dismiss_item)); count += 1
            if count == 0: notif_list.append(widgets.Label(label="No notifications", css_classes=["b-subtext"]))
        except: notif_list.append(widgets.Label(label="Error loading", css_classes=["b-subtext"]))
    utils.Poll(5000, lambda x: refresh_notifications()); refresh_notifications()
    return widgets.Box(vertical=True, css_classes=["dunst-block"], vexpand=True, child=[
        widgets.Box(child=[widgets.Label(label="Notifications", css_classes=["dunst-header"]), widgets.Box(hexpand=True),
                           Block(child=widgets.Label(label="Clear"), css_class="clear-all", on_click=lambda x: [os.system("dunstctl close-all"), HIDDEN_NOTIF_IDS.clear(), refresh_notifications()])]),
        widgets.Box(height_request=10), widgets.Scroll(vexpand=True, child=notif_list)])

# --- РЕЄСТРАЦІЯ ВІКНА (ФІКС ДЛЯ ВАШОЇ ВЕРСІЇ) ---
def create_control_center():
    return widgets.Window(
        name="control_center", 
        namespace="ignis",
        anchor=["top", "right", "bottom"],
        css_classes=["unset-window"],
        visible=False, 
        child=widgets.Box(
            vertical=True, 
            css_classes=["main-bg"], 
            child=[
                widgets.Box(spacing=10, child=[WifiWidget(), BluetoothWidget()]),
                widgets.Box(height_request=15), 
                MusicWidget(), 
                widgets.Box(height_request=15),
                VolumeControl(), 
                widgets.Box(height_request=10), 
                MicrophoneControl(),
                widgets.Box(height_request=15), 
                NotificationWidget()
            ]
        )
    )

# Створюємо вікно
my_win = create_control_center()

# Реєструємо його в додатку, вказуючи і об'єкт, і ім'я
app.add_window(window=my_win, window_name="control_center")

switcher.setup(app)

dock.create_dock()