"""
ClipCollector
=============
Watches your clipboard. Whenever you copy TEXT, a LINK, or an IMAGE,
it waits a few seconds (so you don't fumble a fast double-copy), then
automatically appends it to a running notes file — in order, one after
another — so you never have to manually paste + arrange things.

Run it, minimize it, browse the web, hit Ctrl+C on stuff. Everything
lands in `collected_notes.md` (and images go in `clip_images/`).

--------------------------------------------------------------------
SETUP
--------------------------------------------------------------------
pip install pyperclip pillow

Windows/macOS: that's it, image copy works out of the box (via
Pillow's ImageGrab).

Linux: also install xclip for image support:
    sudo apt install xclip

--------------------------------------------------------------------
RUN
--------------------------------------------------------------------
python clipcollector.py

A small always-on-top window opens showing a live log of what's been
captured. Close the window (or Ctrl+C in the terminal) to stop.

--------------------------------------------------------------------
CONFIG
--------------------------------------------------------------------
Edit the constants below to change delay, output folder/file, etc.
"""

import os
import re
import time
import threading
import datetime
from io import BytesIO

import pyperclip
from PIL import Image, ImageGrab

# ----------------------------- CONFIG ------------------------------
DELAY_SECONDS = 3          # wait this long after a copy before saving
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clip_output")
NOTES_FILE = os.path.join(OUTPUT_DIR, "collected_notes.md")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "clip_images")
POLL_INTERVAL = 0.5         # how often (sec) to check the clipboard for changes
URL_REGEX = re.compile(r"^(https?://|www\.)\S+$", re.IGNORECASE)
# ---------------------------------------------------------------------

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
if not os.path.exists(NOTES_FILE):
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        f.write("# Collected Notes\n\n")


def classify(text):
    if text is None:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    if URL_REGEX.match(stripped):
        return "link"
    return "text"


def append_to_notes(kind, payload, log_callback=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(NOTES_FILE, "a", encoding="utf-8") as f:
        if kind == "link":
            f.write(f"- 🔗 [{payload}]({payload})  _(captured {timestamp})_\n\n")
            preview = payload
        elif kind == "text":
            f.write(f"> {payload}\n\n_(captured {timestamp})_\n\n---\n\n")
            preview = payload[:80] + ("…" if len(payload) > 80 else "")
        elif kind == "image":
            f.write(f"![clip]({payload})  _(captured {timestamp})_\n\n")
            preview = f"[image: {os.path.basename(payload)}]"
        else:
            return
    if log_callback:
        log_callback(kind, preview)


class ClipboardWatcher:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self._running = False
        self._thread = None
        self._last_text = pyperclip.paste()
        self._last_image_hash = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _get_image(self):
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                return img
        except Exception:
            pass
        return None

    def _loop(self):
        while self._running:
            try:
                img = self._get_image()
                if img is not None:
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    img_hash = hash(buf.getvalue())
                    if img_hash != self._last_image_hash:
                        self._last_image_hash = img_hash
                        self._schedule_image(img)
                else:
                    text = pyperclip.paste()
                    if text != self._last_text:
                        self._last_text = text
                        kind = classify(text)
                        if kind:
                            self._schedule_text(kind, text)
            except Exception as e:
                if self.log_callback:
                    self.log_callback("error", str(e))
            time.sleep(POLL_INTERVAL)

    def _schedule_text(self, kind, text):
        def job():
            time.sleep(DELAY_SECONDS)
            # only commit if clipboard hasn't changed again during the delay
            if pyperclip.paste() == text:
                append_to_notes(kind, text, self.log_callback)
        threading.Thread(target=job, daemon=True).start()

    def _schedule_image(self, img):
        def job():
            time.sleep(DELAY_SECONDS)
            filename = f"clip_{int(time.time())}.png"
            path = os.path.join(IMAGES_DIR, filename)
            img.save(path, format="PNG")
            append_to_notes("image", os.path.join("clip_images", filename), self.log_callback)
        threading.Thread(target=job, daemon=True).start()


# ------------------------------ GUI ---------------------------------
def run_gui():
    import tkinter as tk
    from tkinter import scrolledtext

    root = tk.Tk()
    root.title("ClipCollector — running")
    root.geometry("420x320")
    root.attributes("-topmost", True)

    label = tk.Label(root, text=f"Watching clipboard… saving to:\n{NOTES_FILE}",
                      wraplength=400, justify="left", fg="#333")
    label.pack(padx=10, pady=(10, 5), anchor="w")

    log_box = scrolledtext.ScrolledText(root, height=14, wrap="word")
    log_box.pack(padx=10, pady=5, fill="both", expand=True)
    log_box.configure(state="disabled")

    def log_callback(kind, preview):
        def update():
            log_box.configure(state="normal")
            icon = {"link": "🔗", "text": "📝", "image": "🖼️", "error": "⚠️"}.get(kind, "•")
            log_box.insert("end", f"{icon} {preview}\n")
            log_box.see("end")
            log_box.configure(state="disabled")
        root.after(0, update)

    watcher = ClipboardWatcher(log_callback=log_callback)
    watcher.start()

    def on_close():
        watcher.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    print(f"ClipCollector started. Saving to: {NOTES_FILE}")
    print(f"Delay before saving each clip: {DELAY_SECONDS}s")
    try:
        run_gui()
    except Exception as e:
        print("GUI failed to start (headless environment?), falling back to console mode.")
        print(e)
        watcher = ClipboardWatcher(log_callback=lambda k, p: print(f"[{k}] {p}"))
        watcher.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            watcher.stop()
