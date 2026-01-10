import os
import subprocess
import urllib.parse
import hashlib
import gi
from gi.repository import Gio, Gtk, Gdk, GdkPixbuf
from ignis import widgets

# --- НАЛАШТУВАННЯ ---
WALLPAPER_DIR = os.path.expanduser("~/Pictures/wallpapers")
CACHE_DIR = os.path.expanduser("~/.cache/ignis/wallpaper_thumbs")

# Створюємо папку кешу
if not os.path.exists(CACHE_DIR):
    try: os.makedirs(CACHE_DIR)
    except: pass

# Глобальні змінні
wp_window = None
wp_flowbox = None

# --- Custom ClickableBox (Копія з config.py) ---
def ClickableBox(child, on_click, css_classes=[], spacing=0):
    box = widgets.Box(
        child=[child] if child else [],
        css_classes=css_classes,
        spacing=spacing,
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

# --- ЛОГІКА ---

def get_images():
    if not os.path.exists(WALLPAPER_DIR):
        return []
    files = os.listdir(WALLPAPER_DIR)
    images = []
    valid_extensions = [".png", ".jpg", ".jpeg", ".webp"]
    for f in files:
        if any(f.lower().endswith(ext) for ext in valid_extensions):
            images.append(os.path.join(WALLPAPER_DIR, f))
    images.sort()
    return images

def get_thumbnail(original_path):
    """Створює стиснуту копію картинки (300px) для прев'ю"""
    try:
        filename_hash = hashlib.md5(original_path.encode()).hexdigest()
        thumb_path = os.path.join(CACHE_DIR, f"{filename_hash}.png")

        if os.path.exists(thumb_path):
            return thumb_path

        # Масштабуємо до 300px по ширині, висота авто
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(original_path, 300, -1, True)
        pixbuf.savev(thumb_path, "png", [], [])
        return thumb_path
    except Exception as e:
        print(f"Thumb error: {e}")
        return original_path

def set_wallpaper(path):
    cmd = f"swww img '{path}' --transition-type grow --transition-fps 60 --transition-duration 2"
    subprocess.Popen(cmd, shell=True)
    if wp_window:
        wp_window.visible = False

def populate_grid():
    # Очищення
    while wp_flowbox.get_child_at_index(0):
        wp_flowbox.remove(wp_flowbox.get_child_at_index(0))

    images = get_images()
    
    if not images:
        lbl = widgets.Label(label="Немає картинок", css_classes=["wp-error"])
        wp_flowbox.append(lbl)
        return

    for img_path in images:
        filename = os.path.basename(img_path)
        
        # Отримуємо стиснуту мініатюру
        thumb_path = get_thumbnail(img_path)
        safe_thumb_path = urllib.parse.quote(thumb_path)
        
        # Вміст картки
        card_content = widgets.Box(
            vertical=True,
            child=[
                # Пустий блок розтягує картку, щоб текст був знизу
                widgets.Box(hexpand=True, vexpand=True), 
                # Підпис
                widgets.Box(
                    css_classes=["wp-label-box"],
                    child=[widgets.Label(label=filename, css_classes=["wp-label"], ellipsize="end", max_width_chars=18)]
                )
            ]
        )

        # Створюємо кастомну кнопку (ClickableBox)
        # Використовуємо стиль background-image прямо на ній
        btn = ClickableBox(
            child=card_content,
            on_click=lambda x, p=img_path: set_wallpaper(p),
            css_classes=["wp-card"]
        )
        
        # Додаємо стиль через set_style, щоб передати шлях до картинки
        btn.set_style(f"background-image: url('file://{safe_thumb_path}'); background-size: cover; background-position: center;")
        
        wp_flowbox.append(btn)

def on_toggle(action, param):
    if wp_window:
        if wp_window.visible:
            wp_window.visible = False
        else:
            # Запускаємо в окремому потоці, щоб UI не фрізило при генерації перших мініатюр
            # (Тут спрощено, але для першого разу спрацює)
            populate_grid()
            wp_window.visible = True

def setup(app_instance):
    global wp_window, wp_flowbox
    
    wp_flowbox = Gtk.FlowBox()
    wp_flowbox.set_valign(Gtk.Align.START)
    wp_flowbox.set_max_children_per_line(30)
    wp_flowbox.set_min_children_per_line(1)
    wp_flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
    wp_flowbox.set_column_spacing(20)
    wp_flowbox.set_row_spacing(20)

    scroll = widgets.Scroll(
        vexpand=True, 
        hexpand=True,
        child=wp_flowbox,
        css_classes=["wp-scroll"]
    )

    # Кастомна кнопка закриття (ClickableBox)
    close_btn = ClickableBox(
        child=widgets.Label(label="Закрити", css_classes=["wp-close-label"]),
        on_click=lambda x: on_toggle(None, None),
        css_classes=["wp-close-btn"]
    )

    wp_window = widgets.Window(
        name="wallpaper_selector",
        namespace="ignis_wallpapers",
        anchor=[], 
        width_request=950,
        height_request=700,
        exclusivity="ignore",
        layer="overlay",
        visible=False,
        kb_mode="on_demand",
        css_classes=["wp-window"],
        child=widgets.Box(
            vertical=True,
            css_classes=["wp-container"],
            child=[
                widgets.Box( # Header
                    spacing=10,
                    child=[
                        widgets.Label(label="Галерея шпалер", css_classes=["wp-title"], halign="start", hexpand=True),
                        close_btn
                    ]
                ),
                scroll
            ]
        )
    )
    
    app_instance.add_window(window=wp_window, window_name="wallpaper_selector")

    action = Gio.SimpleAction.new("toggle-wallpapers", None)
    action.connect("activate", on_toggle)
    app_instance.add_action(action)