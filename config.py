import sys
import os
import json
import subprocess
import asyncio
import gi
import urllib.parse

# --- ШЛЯХИ ---
sys.path.append(os.path.expanduser("~/.config/ignis"))

# --- ІМПОРТИ ---
import wallpapers
import switcher
import dock

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk
from ignis import widgets, utils
from ignis.app import IgnisApp
from ignis.services.audio import AudioService
from ignis.services.mpris import MprisService
from ignis.services.backlight import BacklightService

app = IgnisApp.get_initialized()
audio = AudioService.get_default()
mpris = MprisService.get_default()
backlight = BacklightService.get_default()

app.apply_css(os.path.expanduser("~/.config/ignis/style.css"))

# --- ДОПОМІЖНІ ФУНКЦІЇ ---
def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    except:
        return ""

def run_async(cmd):
    subprocess.Popen(cmd, shell=True)

def get_wifi_status():
    ssid = run_cmd("nmcli -t -f ACTIVE,SSID dev wifi | grep '^yes' | cut -d: -f2")
    state = run_cmd("nmcli -t -f STATE general")
    return ssid, state == "connected"

def get_bt_status():
    out = run_cmd("bluetoothctl show | grep 'Powered: yes'")
    return bool(out)

# --- CUSTOM CLICKABLE BOX (ВИПРАВЛЕНО ЦЕНТРУВАННЯ) ---
def ClickableBox(child, on_click, css_classes=[], spacing=0, centered=False, **kwargs):
    if centered and child:
        child.set_halign("center")
        child.set_valign("center")
        # ПОВЕРНУВ ЦІ РЯДКИ: вони змушують вміст (іконку/текст) 
        # зайняти весь простір кнопки і стати рівно по центру
        child.set_hexpand(True)
        child.set_vexpand(True)
    
    classes = css_classes + ["unset", "clickable-box"]

    box = widgets.Box(
        child=[child] if child else [],
        css_classes=classes,
        spacing=spacing,
        **kwargs
    )
    
    gesture = Gtk.GestureClick()
    gesture.connect("released", lambda x, n, a, b: on_click(box))
    box.add_controller(gesture)
    
    def on_hover(controller, x, y):
        try: box.set_cursor(Gdk.Cursor.new_from_name("pointer", None))
        except: pass
    
    def on_unhover(controller):
        try: box.set_cursor(None)
        except: pass
    
    motion = Gtk.EventControllerMotion()
    motion.connect("enter", on_hover)
    motion.connect("leave", on_unhover)
    box.add_controller(motion)

    return box

# --- WI-FI WIDGET (WhiteSur Icons) ---
def WifiWidget():
    list_revealer = widgets.Revealer(transition_type="slide_down")
    list_box = widgets.Box(vertical=True, spacing=5, css_classes=["list-container"])
    
    icon_widget = widgets.Icon(image="network-wireless-symbolic", pixel_size=24, css_classes=["b-icon"])
    status_label = widgets.Label(label="Checking...", halign="start", css_classes=["card-status"], ellipsize="end")

    def create_wifi_row(ssid, is_active, strength):
        entry = widgets.Entry(placeholder_text="Password...", css_classes=["wifi-password-entry"], hexpand=True)
        entry.set_visibility(False)
        
        btn_label = widgets.Label(label="Connect", style="font-weight: bold; color: #1e1e2e;")
        btn_connect = ClickableBox(
            child=btn_label,
            css_classes=["wifi-connect-btn"],
            on_click=lambda x: run_async(f"nmcli dev wifi connect '{ssid}' password '{entry.get_text()}'"),
            centered=True
        )
        
        password_area = widgets.Box(spacing=5, child=[entry, btn_connect])
        pass_revealer = widgets.Revealer(transition_type="slide_down", child=password_area, reveal_child=False)

        def on_click_network(x):
            if is_active:
                run_async(f"nmcli connection down id '{ssid}'")
            else:
                try:
                    saved = run_cmd(f"nmcli -t -f NAME connection show | grep '^{ssid}$'")
                    if saved:
                        run_async(f"nmcli connection up id '{ssid}'")
                    else:
                        pass_revealer.set_reveal_child(not pass_revealer.get_reveal_child())
                except:
                    pass_revealer.set_reveal_child(not pass_revealer.get_reveal_child())

        row_content = widgets.Box(spacing=10, child=[
            widgets.Icon(image="network-wireless-symbolic", pixel_size=20, css_classes=["list-icon"]),
            widgets.Label(label=f"{ssid} ({strength}%)", css_classes=["list-label"], ellipsize="end", halign="start", hexpand=True),
            widgets.Icon(image="object-select-symbolic" if is_active else "", pixel_size=16, css_classes=["list-status"])
        ])

        item_box = widgets.Box(vertical=True, css_classes=["list-item"], child=[
            ClickableBox(child=row_content, on_click=on_click_network, hexpand=True),
            pass_revealer
        ])
        if is_active: item_box.add_css_class("list-item-active")
        return item_box

    def refresh_wifi_list():
        child = list_box.get_first_child()
        while child: list_box.remove(child); child = list_box.get_first_child()
        list_box.append(widgets.Label(label="Scanning...", css_classes=["b-subtext"]))
        
        def scan_process():
            try:
                run_cmd("nmcli dev wifi rescan") 
                raw = run_cmd("nmcli -t -f SSID,IN-USE,SIGNAL dev wifi list")
                child = list_box.get_first_child()
                while child: list_box.remove(child); child = list_box.get_first_child()
                
                lines = raw.split('\n'); unique_ssids = set(); count = 0
                for line in lines:
                    if not line: continue
                    parts = line.split(':')
                    if len(parts) < 3: continue
                    ssid = parts[0]; is_active = (parts[1] == "yes"); strength = parts[2]
                    if not ssid or ssid in unique_ssids: continue
                    unique_ssids.add(ssid)
                    list_box.append(create_wifi_row(ssid, is_active, strength))
                    count += 1
                    if count > 15: break
                if count == 0: list_box.append(widgets.Label(label="No networks", css_classes=["b-subtext"]))
            except: list_box.append(widgets.Label(label="Error", css_classes=["b-subtext"]))
        utils.Timeout(100, scan_process)

    def toggle_list(widget):
        is_open = list_revealer.get_reveal_child()
        if not is_open: refresh_wifi_list()
        list_revealer.set_reveal_child(not is_open)

    def poll_status(widget):
        ssid, connected = get_wifi_status()
        if not ssid:
            radio = run_cmd("nmcli radio wifi")
            if radio == "disabled":
                status_label.set_label("Disabled")
                icon_widget.set_image("network-wireless-disabled-symbolic")
                icon_widget.add_css_class("dim-icon")
            else:
                status_label.set_label("Disconnected")
                icon_widget.set_image("network-wireless-offline-symbolic")
                icon_widget.add_css_class("dim-icon")
        else:
            status_label.set_label(ssid)
            icon_widget.set_image("network-wireless-connected-symbolic")
            icon_widget.add_css_class("accent-icon")
    
    utils.Poll(2000, lambda x: poll_status(None))

    power_btn = ClickableBox(
        child=widgets.Icon(image="system-shutdown-symbolic", pixel_size=20), 
        css_classes=["power-btn"],
        on_click=lambda x: run_async("nmcli radio wifi off" if run_cmd("nmcli radio wifi") == "enabled" else "nmcli radio wifi on"),
        centered=True
    )
    
    header_left = ClickableBox(
        child=widgets.Box(spacing=12, child=[
            icon_widget, 
            widgets.Box(vertical=True, valign="center", child=[
                widgets.Label(label="Wi-Fi", halign="start", css_classes=["card-title"]), 
                status_label
            ])
        ]),
        on_click=toggle_list, css_classes=["header-left"],
        hexpand=True
    )
    header = widgets.Box(spacing=0, child=[header_left, widgets.Box(hexpand=True), power_btn])
    scroll = widgets.Scroll(height_request=250, child=list_box); list_revealer.set_child(scroll)
    return widgets.Box(vertical=True, css_classes=["block", "dark", "wide"], child=[widgets.Box(css_classes=["header-padding"], child=[header]), list_revealer])

# --- BLUETOOTH WIDGET (WhiteSur Icons) ---
bt_scan_process = None

def BluetoothWidget():
    list_revealer = widgets.Revealer(transition_type="slide_down")
    list_box = widgets.Box(vertical=True, spacing=5, css_classes=["list-container"])
    
    icon_widget = widgets.Icon(image="bluetooth-active-symbolic", pixel_size=24, css_classes=["b-icon"])
    status_label = widgets.Label(label="Checking...", halign="start", css_classes=["card-status"])
    scan_btn_label = widgets.Label(label="Scan")

    def toggle_scan(btn_box):
        global bt_scan_process
        if bt_scan_process:
            run_async("bluetoothctl scan off")
            bt_scan_process = None
            scan_btn_label.set_label("Scan")
            btn_box.remove_css_class("active-scan-btn")
        else:
            run_async("bluetoothctl scan on")
            bt_scan_process = True
            scan_btn_label.set_label("Stop")
            btn_box.add_css_class("active-scan-btn")
            refresh_bt_list()

    def create_bt_row(mac, name, is_connected, is_paired):
        pair_label = widgets.Label(label="Pair & Connect", style="color: #1e1e2e; font-weight: bold;")
        pair_btn = ClickableBox(
            child=pair_label,
            css_classes=["wifi-connect-btn"],
            on_click=lambda x: run_async(f"bluetoothctl trust {mac} && bluetoothctl pair {mac} && bluetoothctl connect {mac}"),
            centered=True
        )
        action_revealer = widgets.Revealer(transition_type="slide_down", child=widgets.Box(child=[pair_btn]), reveal_child=False)

        def on_click_device(x):
            if is_connected:
                run_async(f"bluetoothctl disconnect {mac}")
            elif is_paired:
                run_async(f"bluetoothctl connect {mac}")
            else:
                action_revealer.set_reveal_child(not action_revealer.get_reveal_child())

        status_icon_name = "object-select-symbolic" if is_connected else ("network-wired-symbolic" if is_paired else "")
        
        row_content = widgets.Box(spacing=10, child=[
            widgets.Icon(image="bluetooth-symbolic", pixel_size=20, css_classes=["list-icon"]),
            widgets.Label(label=name if name else mac, css_classes=["list-label"], ellipsize="end", halign="start", hexpand=True),
            widgets.Icon(image=status_icon_name, pixel_size=16, css_classes=["list-status"])
        ])

        item_box = widgets.Box(vertical=True, css_classes=["list-item"], child=[
            ClickableBox(child=row_content, on_click=on_click_device, hexpand=True),
            action_revealer
        ])
        if is_connected: item_box.add_css_class("list-item-active")
        return item_box

    def refresh_bt_list():
        if not list_revealer.get_reveal_child(): return
        child = list_box.get_first_child()
        while child: list_box.remove(child); child = list_box.get_first_child()
        try:
            raw = run_cmd("bluetoothctl devices")
            lines = raw.split('\n'); count = 0
            for line in lines:
                if not line: continue
                parts = line.split(' ', 2)
                if len(parts) < 3: continue
                mac = parts[1]; name = parts[2]
                info = run_cmd(f"bluetoothctl info {mac}")
                is_connected = "Connected: yes" in info
                is_paired = "Paired: yes" in info
                list_box.append(create_bt_row(mac, name, is_connected, is_paired))
                count += 1
            if count == 0: 
                list_box.append(widgets.Label(label="No devices found", css_classes=["b-subtext"]))
                if not bt_scan_process:
                    list_box.append(widgets.Label(label="Press Scan to find new", css_classes=["b-subtext"]))
        except: list_box.append(widgets.Label(label="Error", css_classes=["b-subtext"]))
        
        if bt_scan_process:
            utils.Timeout(2000, refresh_bt_list)

    def toggle_list(widget):
        is_open = list_revealer.get_reveal_child()
        if not is_open: refresh_bt_list()
        list_revealer.set_reveal_child(not is_open)

    def poll_status(widget):
        is_on = get_bt_status()
        status_label.set_label("On" if is_on else "Off")
        icon_widget.set_image("bluetooth-active-symbolic" if is_on else "bluetooth-disabled-symbolic")
        if is_on: icon_widget.add_css_class("accent-icon"); icon_widget.remove_css_class("dim-icon")
        else: icon_widget.add_css_class("dim-icon"); icon_widget.remove_css_class("accent-icon")

    utils.Poll(2000, lambda x: poll_status(None))

    scan_btn = ClickableBox(
        child=scan_btn_label, css_classes=["wifi-connect-btn"],
        on_click=toggle_scan, centered=True
    )
    power_btn = ClickableBox(
        child=widgets.Icon(image="system-shutdown-symbolic", pixel_size=20), 
        css_classes=["power-btn"],
        on_click=lambda x: run_async("bluetoothctl power off" if get_bt_status() else "bluetoothctl power on"),
        centered=True
    )
    header_left = ClickableBox(
        child=widgets.Box(spacing=12, child=[
            icon_widget, 
            widgets.Box(vertical=True, valign="center", child=[
                widgets.Label(label="Bluetooth", halign="start", css_classes=["card-title"]), 
                status_label
            ])
        ]),
        on_click=toggle_list, css_classes=["header-left"],
        hexpand=True
    )
    header = widgets.Box(spacing=5, child=[header_left, widgets.Box(hexpand=True), scan_btn, power_btn])
    scroll = widgets.Scroll(height_request=250, child=list_box); list_revealer.set_child(scroll)
    return widgets.Box(vertical=True, css_classes=["block", "dark", "wide"], child=[widgets.Box(css_classes=["header-padding"], child=[header]), list_revealer])

# --- МЕДІА ВІДЖЕТ (WhiteSur Icons) ---
def MediaWidget():
    players_box = widgets.Box(vertical=True, spacing=10)

    def get_art_css(url):
        if not url: return ""
        if not url.startswith("http") and not url.startswith("file"):
            url = "file://" + url
        return f"background-image: url('{url}'); background-size: cover; background-position: center;"

    def on_player_added(service, player):
        player_widget = widgets.Box(
            vertical=True,
            css_classes=["music-box"], 
            child=[
                widgets.Box(spacing=15, child=[
                    widgets.Box(
                        css_classes=["music-art-icon"],
                        style=player.bind("art_url", get_art_css),
                        child=[
                            widgets.Icon(image="folder-music-symbolic", visible=player.bind("art_url", lambda u: not u), pixel_size=32)
                        ]
                    ),
                    widgets.Box(vertical=True, valign="center", hexpand=True, child=[
                        widgets.Label(
                            label=player.bind("title"), 
                            halign="start", ellipsize="end", css_classes=["music-title"]
                        ),
                        widgets.Label(
                            label=player.bind("artist"), 
                            halign="start", ellipsize="end", css_classes=["music-artist"]
                        )
                    ])
                ]),
                widgets.Scale(
                    hexpand=True,
                    css_classes=["b-slider", "media-scale"],
                    min=0,
                    max=player.bind("length"),
                    value=player.bind("position"),
                    on_change=lambda x: player.set_position(x.value),
                    visible=player.bind("length", lambda l: l > 0)
                ),
                widgets.Box(height_request=5),
                widgets.Box(halign="center", spacing=20, child=[
                    # Іконки керування
                    ClickableBox(
                        child=widgets.Icon(image="media-skip-backward-symbolic", pixel_size=24), 
                        on_click=lambda x: player.previous(), 
                        css_classes=["control-btn"], centered=True
                    ),
                    ClickableBox(
                        child=widgets.Icon(
                            image=player.bind("playback_status", lambda s: "media-playback-pause-symbolic" if s == "Playing" else "media-playback-start-symbolic"),
                            pixel_size=32
                        ), 
                        on_click=lambda x: player.play_pause(), 
                        css_classes=["play-btn"], spacing=0, centered=True
                    ),
                    ClickableBox(
                        child=widgets.Icon(image="media-skip-forward-symbolic", pixel_size=24), 
                        on_click=lambda x: player.next(), 
                        css_classes=["control-btn"], centered=True
                    )
                ])
            ]
        )
        
        player.connect("closed", lambda x: players_box.remove(player_widget))
        players_box.append(player_widget)

    mpris.connect("player-added", on_player_added)
    for p in mpris.players:
        on_player_added(mpris, p)

    return widgets.Box(
        vertical=True, 
        child=[
            players_box,
            widgets.Box(
                visible=mpris.bind("players", lambda p: len(p) == 0),
                css_classes=["music-box"],
                child=[widgets.Label(label="No Media Playing", css_classes=["music-title"], halign="center")]
            )
        ]
    )

# --- VOLUME WIDGET (WhiteSur Icons) ---
def VolumeSlider(stream_type):
    stream = getattr(audio, stream_type)
    
    icon_box = ClickableBox(
        child=widgets.Icon(image=stream.bind("icon_name"), pixel_size=20),
        css_classes=["b-icon-btn"], 
        on_click=lambda x: stream.set_is_muted(not stream.is_muted),
        centered=True
    )

    scale = widgets.Scale(
        min=0, max=100, step=1, hexpand=True, 
        css_classes=["b-slider"],
        value=stream.bind("volume"),
        on_change=lambda x: stream.set_volume(x.value)
    )

    return widgets.Box(
        css_classes=["block", "dark", "wide"], 
        spacing=10, 
        child=[icon_box, scale]
    )

# --- BRIGHTNESS WIDGET (WhiteSur Icons) ---
def BrightnessSlider():
    return widgets.Box(
        visible=backlight.bind("available"),
        css_classes=["block", "dark", "wide"], 
        spacing=10, 
        child=[
            widgets.Icon(image="display-brightness-symbolic", pixel_size=20, css_classes=["b-icon"]),
            widgets.Scale(
                min=0, max=backlight.max_brightness, hexpand=True,
                css_classes=["b-slider"],
                value=backlight.bind("brightness"),
                on_change=lambda x: backlight.set_brightness(x.value)
            )
        ]
    )

# --- СПОВІЩЕННЯ (WhiteSur Icons) ---
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
    
    # Кнопка очищення з іконкою
    clear_btn = widgets.Box(
        child=[
            widgets.Box(
                css_classes=["block", "std"], 
                child=[
                    ClickableBox(
                        child=widgets.Icon(image="user-trash-symbolic", pixel_size=18),
                        on_click=lambda x: [os.system("dunstctl close-all"), HIDDEN_NOTIF_IDS.clear(), refresh_notifications()],
                        centered=True
                    )
                ]
            )
        ]
    )

    return widgets.Box(vertical=True, css_classes=["dunst-block"], vexpand=True, child=[
        widgets.Box(child=[widgets.Label(label="Notifications", css_classes=["dunst-header"]), widgets.Box(hexpand=True),
                           clear_btn]),
        widgets.Box(height_request=10), widgets.Scroll(vexpand=True, child=notif_list)])


# --- WINDOW SETUP ---
def create_control_center():
    return widgets.Window(
        name="control_center", namespace="ignis", anchor=["top", "right", "bottom"], css_classes=["unset-window"], visible=False,
        child=widgets.Box(vertical=True, css_classes=["main-bg"], child=[
            widgets.Box(spacing=10, child=[WifiWidget(), BluetoothWidget()]),
            widgets.Box(height_request=15), 
            MediaWidget(),
            widgets.Box(height_request=15), 
            VolumeSlider("speaker"),
            widgets.Box(height_request=10), 
            VolumeSlider("microphone"),
            widgets.Box(height_request=10),
            BrightnessSlider(),
            widgets.Box(height_request=15), 
            NotificationWidget()
        ])
    )

app.add_window(window=create_control_center(), window_name="control_center")

try:
    switcher.setup(app)
    wallpapers.setup(app)
except Exception as e: print(e)

dock.create_dock()
