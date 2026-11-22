def register(app, callback):
    """Grab only the requested X11 chord. Qt watches the dedicated X connection."""
    from Xlib import X, XK, display
    from PyQt5.QtCore import QSocketNotifier
    d = display.Display()
    root = d.screen().root
    key = d.keysym_to_keycode(XK.string_to_keysym("v"))
    errors = []
    for extra in (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask):
        root.grab_key(key, X.ControlMask | X.ShiftMask | extra, False,
                      X.GrabModeAsync, X.GrabModeAsync,
                      onerror=lambda err, req: errors.append(err) or True)
    d.sync()
    if errors:
        d.close()
        raise RuntimeError("Atalho ocupado por outro aplicativo.")
    notifier = QSocketNotifier(d.fileno(), QSocketNotifier.Read, app)
    def drain(_):
        while d.pending_events():
            if d.next_event().type == X.KeyPress:
                callback()
    notifier.activated.connect(drain)
    app.aboutToQuit.connect(d.close)
    return notifier

