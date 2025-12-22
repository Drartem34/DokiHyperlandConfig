import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

def run():
    # Підключаємося до сесії
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    
    # ID програми Ignis
    app_id = "com.github.linkfrg.ignis"
    object_path = "/com/github/linkfrg/ignis"
    
    # Формуємо повідомлення для активації дії
    message = Gio.DBusMessage.new_method_call(
        app_id,
        object_path,
        "org.gtk.Actions",
        "Activate"
    )
    # Передаємо назву дії "toggle-switcher", параметри [] та метадані {}
    message.set_body(GLib.Variant("(sava{sv})", ("toggle-switcher", [], {})))
    
    try:
        bus.send_message_with_reply_sync(message, Gio.DBusSendMessageFlags.NONE, -1)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run()