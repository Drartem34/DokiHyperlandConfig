import subprocess
import json
import os
import threading
import time
from gi.repository import Gio, Gtk, GLib
from ignis import widgets

# --- НАЛАШТУВАННЯ ОПТИМІЗАЦІЇ ---
HOME = os.path.expanduser("~")
CACHE_DIR = os.path.join(HOME, ".config", "ignis", "cache")
# Як часто оновлювати скріншот АКТИВНОГО вікна (в секундах)
# 5-10 секунд - це оптимально. 
UPDATE_INTERVAL = 30 

if not os.path.exists(CACHE_DIR):
    try: os.makedirs(CACHE_DIR)
    except: pass

# Глобальні змінні
switcher_window = None
items_box = None
windows_list = []
current_index = 0

# --- ЕКОНОМНИЙ СКРІНШОТЕР ---
def smart_screenshot_loop():
    """
    Робить скріншот ТІЛЬКИ активного вікна.
    Це економить 90% ресурсів, бо фонові вікна не скануються.
    """
    last_addr = None
    
    while True:
        try:
            # 1. Отримуємо інформацію ТІЛЬКИ про активне вікно (це дуже швидко)
            # Використовуємо activewindow замість clients, щоб не парсити все
            try:
                active_window = json.loads(subprocess.check_output(["hyprctl", "activewindow", "-j"], text=True))
            except:
                active_window = {}

            # Перевіряємо, чи є валідна адреса
            if active_window and "address" in active_window and active_window["class"] != "ignis":
                addr = active_window["address"]
                at = active_window["at"]
                size = active_window["size"]
                
                # Шлях збереження
                path = os.path.join(CACHE_DIR, f"{addr}.png")
                geometry = f"{at[0]},{at[1]} {size[0]}x{size[1]}"
                
                # 2. Робимо скріншот
                # grim дуже легкий, якщо робити один знімок раз на 5 секунд
                subprocess.run(f"grim -l 0 -g '{geometry}' {path}", shell=True, timeout=1)
                
        except Exception as e:
            # Тихо ігноруємо помилки, щоб не спамити в лог
            pass
            
        # Спимо заданий час
        time.sleep(UPDATE_INTERVAL)

# Запускаємо економний режим
threading.Thread(target=smart_screenshot_loop, daemon=True).start()


# --- ІНТЕРФЕЙС (Майже без змін) ---

def get_windows():
    try:
        ret = subprocess.check_output(["hyprctl", "clients", "-j"], text=True)
        data = json.loads(ret)
        data.sort(key=lambda x: x.get('focusHistoryID', 0))
        return data
    except:
        return []

def activate_selected():
    global switcher_window
    if not windows_list: return
    try:
        target = windows_list[current_index]
        address = target.get("address", "")
        subprocess.Popen(f"hyprctl dispatch focuswindow address:{address}", shell=True)
    except: pass
    
    if switcher_window:
        switcher_window.visible = False

def update_selection_visuals():
    child = items_box.get_first_child()
    idx = 0
    while child:
        if idx == current_index:
            child.add_css_class("selected")
        else:
            child.remove_css_class("selected")
        child = child.get_next_sibling()
        idx += 1

def step_next(action, param):
    global current_index, windows_list, switcher_window
    
    if not switcher_window: return

    if not switcher_window.visible:
        rebuild_list()
        switcher_window.visible = True
        current_index = 1 if len(windows_list) > 1 else 0
    else:
        current_index += 1
        if current_index >= len(windows_list):
            current_index = 0
    
    update_selection_visuals()

def on_release(action, param):
    if switcher_window and switcher_window.visible:
        activate_selected()

def rebuild_list():
    global windows_list
    
    child = items_box.get_first_child()
    while child:
        items_box.remove(child)
        child = items_box.get_first_child()

    raw_windows = get_windows()
    windows_list = []

    for c in raw_windows:
        if c["class"] == "ignis" or not c["title"]: continue
        windows_list.append(c)
        
        addr = c["address"]
        cache_path = os.path.join(CACHE_DIR, f"{addr}.png")
        
        # Логіка прев'ю:
        # Ми просто читаємо файл. Якщо ти був у цьому вікні 5 хвилин тому -
        # там буде картинка 5-хвилинної давності. Це нормально для прев'ю.
        if os.path.exists(cache_path):
            # ?t=... змушує оновити кеш зображення при відкритті меню
            style_css = f"background-image: url('file://{cache_path}?t={time.time()}');"
            preview_widget = widgets.Box(css_classes=["preview-image"], style=style_css)
        else:
            icon_name = c.get("class", "").lower()
            if "code" in icon_name: icon_name = "visual-studio-code"
            if "telegram" in icon_name: icon_name = "telegram"
            if "firefox" in icon_name: icon_name = "firefox"
            preview_widget = widgets.Icon(image=icon_name, pixel_size=64, style="margin: 24px;")

        item = widgets.Box(
            vertical=True,
            css_classes=["switcher-item"],
            child=[
                preview_widget,
                widgets.Label(label=c.get("title", "")[:20], css_classes=["switcher-label"])
            ]
        )
        items_box.append(item)

def setup(app_instance):
    global switcher_window, items_box
    
    items_box = widgets.Box(spacing=15, halign="center", valign="center")
    
    switcher_window = widgets.Window(
        name="switcher",
        namespace="ignis_switcher",
        anchor=[], 
        exclusivity="ignore",
        layer="overlay",
        visible=False,
        kb_mode="on_demand",
        css_classes=["switcher-bg"],
        child=widgets.Box(css_classes=["switcher-container"], child=[items_box])
    )
    
    app_instance.add_window(window=switcher_window, window_name="switcher")

    action_next = Gio.SimpleAction.new("switcher-next", None)
    action_next.connect("activate", step_next)
    app_instance.add_action(action_next)

    action_release = Gio.SimpleAction.new("switcher-release", None)
    action_release.connect("activate", on_release)
    app_instance.add_action(action_release)