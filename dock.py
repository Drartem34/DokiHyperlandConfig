import os
import json
import subprocess
from ignis import widgets, utils
from ignis.services.applications import ApplicationsService
from gi.repository import Gtk, Gdk

apps_service = ApplicationsService.get_default()

# --- СПИСОК ПРОГРАМ, ПРИ ЯКИХ ДОК НЕ ХОВАЄТЬСЯ ---
# Вписуй сюди 'class' вікна (можна частину назви)
ALWAYS_VISIBLE_APPS = [
    "nautilus",
    "kitty",
    "wezterm",
    "ignis" 
]

# --- HELPER FUNCTIONS ---

def get_hyprland_clients():
    try:
        output = subprocess.check_output(["hyprctl", "clients", "-j"], text=True)
        return json.loads(output)
    except Exception:
        return []

def get_active_window_info():
    """Отримує інформацію про активне вікно (адреса і клас)"""
    try:
        output = subprocess.check_output(["hyprctl", "activewindow", "-j"], text=True)
        return json.loads(output)
    except Exception:
        return {}

def get_active_workspace_id():
    try:
        output = subprocess.check_output(["hyprctl", "activeworkspace", "-j"], text=True)
        data = json.loads(output)
        return data.get("id", 1)
    except Exception:
        return 1

def activate_window(address):
    subprocess.Popen(f"hyprctl dispatch focuswindow address:{address}", shell=True)

# --- DOCK ITEM ---

def DockAppItem(app, window_address, is_active):
    icon = widgets.Icon(
        image=app.icon,
        pixel_size=47, 
        style="border-radius: 12px;" 
    )

    css_classes = ["dock-item"]
    
    base_margin = 8 
    jump_height = 5
    
    if is_active:
        mb_val = base_margin + jump_height 
        css_classes.append("active")
    else:
        mb_val = base_margin
    
    style_css = f"""
        margin-left: 4px; 
        margin-right: 4px; 
        margin-bottom: {mb_val}px; 
        padding: 0px; 
        border-radius: 12px; 
        transition: all 0.2s cubic-bezier(0.25, 1, 0.5, 1);
    """

    container = widgets.Box(
        child=[icon],
        css_classes=css_classes,
        style=style_css,
        valign="end" 
    )

    gesture = Gtk.GestureClick()
    gesture.connect("released", lambda *args: activate_window(window_address))
    container.add_controller(gesture)
    container.set_cursor_from_name("pointer")

    return container

# --- WIDGETS ---

def DockWidget():
    content = widgets.Box(spacing=0, css_classes=["dock-content"])
    content.set_valign("end") 
    content.set_size_request(-1, 64) 

    def update_dock(*args):
        child = content.get_first_child()
        while child:
            content.remove(child)
            child = content.get_first_child()
        
        windows = get_hyprland_clients()
        active_info = get_active_window_info()
        active_addr = active_info.get("address", "")
        
        windows.sort(key=lambda x: x.get("workspace", {}).get("id", 0))

        unique_apps = {} 
        app_order = []

        for w in windows:
            w_class = w.get("class", "").lower()
            w_initial = w.get("initialClass", "").lower()
            w_address = w.get("address", "") 
            is_active_window = (w_address == active_addr)

            for app in apps_service.apps:
                app_id = app.id.lower().replace(".desktop", "")
                app_name = app.name.lower()

                if (app_id in w_class or w_class in app_id or
                    app_name in w_class or app_id in w_initial):

                    if app.id not in unique_apps:
                        unique_apps[app.id] = {
                            "app": app,
                            "address": w_address,
                            "is_active": is_active_window
                        }
                        app_order.append(app.id)
                    else:
                        if is_active_window:
                            unique_apps[app.id]["is_active"] = True
                            unique_apps[app.id]["address"] = w_address
                    break 

        for app_id in app_order:
            data = unique_apps[app_id]
            content.append(DockAppItem(data["app"], data["address"], data["is_active"]))

    utils.Poll(500, update_dock)
    update_dock()
    
    return widgets.Box(child=[content], css_classes=["dock-main"])
    
def WorkspaceWidget():
    label = widgets.Label(label="  1", css_classes=["sys-text"])
    
    def update_ws(*args):
        ws_id = get_active_workspace_id()
        label.set_label(f"ㅤ ㅤ {ws_id}")

    utils.Poll(200, update_ws)
    
    return widgets.Box(
        css_classes=["sys-monitor", "ws-monitor"],
        child=[label],
        valign="center"
    )

def SysMonitorWidget():
    cpu_label = widgets.Label(label=" 0%", css_classes=["sys-text"])
    ram_label = widgets.Label(label=" 0%", css_classes=["sys-text"])
    
    def update_stats(*args):
        try:
            with os.popen("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'") as f:
                cpu = f.read().strip().replace(',', '.')
            if cpu: cpu_label.set_label(f" ㅤ{int(float(cpu))}%")
            
            with os.popen("free -m | grep Mem") as f:
                mem = f.read().split()
            if len(mem) >= 3:
                ram_label.set_label(f" ㅤ{int((int(mem[2]) / int(mem[1])) * 100)}%")
        except: pass

    utils.Poll(2000, update_stats)
    return widgets.Box(
        vertical=True, 
        valign="center", 
        spacing=2, 
        css_classes=["sys-monitor"], 
        child=[cpu_label, ram_label]
    )

# --- АВТО-ПРИХОВУВАННЯ З БІЛИМ СПИСКОМ ---

cached_monitor_height = 0
cached_monitor_width = 0

def get_monitor_size():
    global cached_monitor_height, cached_monitor_width
    if cached_monitor_height == 0:
        try:
            output = subprocess.check_output(["hyprctl", "monitors", "-j"], text=True)
            data = json.loads(output)
            cached_monitor_height = data[0]["height"]
            cached_monitor_width = data[0]["width"]
        except:
            cached_monitor_height = 1080
            cached_monitor_width = 1920
    return cached_monitor_width, cached_monitor_height

def setup_autohide(revealer):
    def check_state(*args):
        try:
            # 1. Отримуємо позицію миші
            pos_raw = subprocess.check_output(["hyprctl", "cursorpos"], text=True).strip()
            x, y = map(int, pos_raw.split(","))
            width, height = get_monitor_size()
            
            trigger_height = 10 
            dock_visible_area = 100 
            center_start = width * 0.3
            center_end = width * 0.7

            mouse_is_bottom = False
            if revealer.get_reveal_child():
                if y > (height - dock_visible_area): mouse_is_bottom = True
            else:
                if y > (height - trigger_height) and (center_start < x < center_end):
                    mouse_is_bottom = True

            # 2. Отримуємо активне вікно
            active_info = get_active_window_info()
            has_active_window = bool(active_info.get("address", ""))
            active_class = active_info.get("class", "").lower()

            # 3. Перевіряємо білий список
            is_ignored_app = False
            if has_active_window:
                for app_name in ALWAYS_VISIBLE_APPS:
                    if app_name.lower() in active_class:
                        is_ignored_app = True
                        break

            # 4. Логіка відображення
            should_show = False
            
            if mouse_is_bottom:
                should_show = True # Миша внизу - завжди показуємо
            elif not has_active_window:
                should_show = True # Робочий стіл - показуємо
            elif is_ignored_app:
                should_show = True # Програма зі списку - показуємо
            else:
                should_show = False # Звичайна програма - ховаємо
            
            revealer.set_reveal_child(should_show)
            
        except Exception:
            pass

    utils.Poll(200, check_state)


# --- MAIN LAYOUT ---
def create_dock():
    dock_content = widgets.Box(
        spacing=15,
        css_classes=["dock-wrapper"],
        valign="end", 
        child=[
            DockWidget(),      
            WorkspaceWidget(), 
            SysMonitorWidget() 
        ]
    )

    revealer = widgets.Revealer(
        transition_type="slide_up",
        transition_duration=300,
        reveal_child=True, 
        child=dock_content
    )

    setup_autohide(revealer)

    return widgets.Window(
        name="dock",
        namespace="ignis_dock",
        anchor=["bottom"],
        exclusivity="ignore", 
        layer="top",
        css_classes=["unset-window"],
        child=widgets.Box(
            child=[revealer],
            halign="center" 
        )
    )
