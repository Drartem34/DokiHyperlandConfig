import os
import json
import subprocess
from ignis import widgets, utils
from ignis.services.applications import ApplicationsService
from gi.repository import Gtk

apps_service = ApplicationsService.get_default()

def get_hyprland_clients():
    """Отримує список вікон з Hyprland у форматі JSON"""
    try:
        output = subprocess.check_output(["hyprctl", "clients", "-j"], text=True)
        return json.loads(output)
    except Exception:
        return []

def get_active_window_address():
    """Отримує адресу активного вікна (фокус)"""
    try:
        output = subprocess.check_output(["hyprctl", "activewindow", "-j"], text=True)
        data = json.loads(output)
        return data.get("address", "")
    except Exception:
        return ""

def activate_window(address):
    """Перемикає фокус на вікно за його адресою"""
    subprocess.Popen(f"hyprctl dispatch focuswindow address:{address}", shell=True)

def DockAppItem(app, window_address, is_active):
    # --- ЗБІЛЬШЕНИЙ МАСШТАБ ---
    icon = widgets.Icon(
        image=app.icon,
        pixel_size=47, 
        style="border-radius: 12px;" 
    )

    # Визначаємо класи (додаємо 'active', якщо вікно активне)
    css_classes = ["dock-item"]
    if is_active:
        css_classes.append("active")

    # Використовуємо Box (без білого фону)
    container = widgets.Box(
        child=[icon],
        css_classes=css_classes,
        style="margin: 0px 4px; padding: 0px; border-radius: 12px; transition: 0.2s;"
    )

    # --- ЛОГІКА ПЕРЕМИКАННЯ (ФОКУС) ---
    gesture = Gtk.GestureClick()
    gesture.connect("released", lambda *args: activate_window(window_address))
    container.add_controller(gesture)
    container.set_cursor_from_name("pointer")

    return container

def DockWidget():
    content = widgets.Box(spacing=5, css_classes=["dock-content"])

    def update_dock(*args):
        child = content.get_first_child()
        while child:
            content.remove(child)
            child = content.get_first_child()
        
        # Отримуємо вікна та адресу активного вікна
        windows = get_hyprland_clients()
        active_addr = get_active_window_address()
        
        added_apps = set()

        # Сортуємо: активне вікно ставимо першим у списку обробки.
        # Це гарантує, що якщо відкрито 2 вікна Firefox, іконка підсвітиться для активного.
        windows.sort(key=lambda x: x.get("address") == active_addr, reverse=True)

        # Проходимося по кожному відкритому вікну
        for w in windows:
            w_class = w.get("class", "").lower()
            w_initial = w.get("initialClass", "").lower()
            w_title = w.get("title", "").lower()
            w_address = w.get("address", "") 
            
            # Перевіряємо, чи це вікно активне
            is_active = (w_address == active_addr)

            # Шукаємо, яка програма відповідає цьому вікну
            for app in apps_service.apps:
                if app.id in added_apps:
                    continue

                app_id = app.id.lower().replace(".desktop", "")
                app_name = app.name.lower()

                # Перевірка збігу
                is_match = (
                    app_id in w_class or w_class in app_id or
                    app_name in w_class or
                    app_id in w_initial
                )

                if is_match:
                    # Передаємо is_active у кнопку
                    content.append(DockAppItem(app, w_address, is_active))
                    added_apps.add(app.id)
                    break 

    # Оновлення кожні 500мс (швидше, щоб підсвітка реагувала миттєво)
    utils.Poll(500, update_dock)
    update_dock()
    
    return widgets.Box(child=[content], css_classes=["dock-main"])

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
    return widgets.Box(vertical=True, valign="center", spacing=2, css_classes=["sys-monitor"], child=[cpu_label, ram_label])

def create_dock():
    return widgets.Window(
        name="dock",
        namespace="ignis_dock",
        anchor=["bottom"],
        exclusivity="exclusive",
        css_classes=["unset-window"],
        child=widgets.Box(
            spacing=15,
            css_classes=["dock-wrapper"],
            child=[DockWidget(), SysMonitorWidget()]
        )
    )