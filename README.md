# ClipCollector — Stage 1

A tiny background tool: copy text, a link, or an image anywhere (browser,
PDF, anywhere), wait ~3 seconds, and it's automatically appended — in
order — to one running notes file. No manual pasting or arranging.

## Quick start

```bash
pip install -r requirements.txt
python clipcollector.py
```

A small always-on-top window pops up showing a live log of what's been
captured. Everything is saved to:

```
clip_output/collected_notes.md   <- text, links, and image references
clip_output/clip_images/         <- actual image files
```

`collected_notes.md` is plain Markdown, so it opens nicely in Obsidian,
VS Code, Typora, or you can paste its contents straight into Google Docs.

## How it works

- Polls the clipboard every 0.5s.
- Detects whether the new clipboard content is a URL, plain text, or an
  image (via Pillow's `ImageGrab`, which also reads clipboard images on
  Windows/macOS; on Linux install `xclip` for the same support: `sudo apt
  install xclip`).
- Waits `DELAY_SECONDS` (default 3) — if you copy something else in that
  window, the first one is skipped so a fast double-copy doesn't produce
  duplicates.
- Appends it to `collected_notes.md` with a timestamp, in the order you
  copied things.

## Tweakable settings (top of `clipcollector.py`)

- `DELAY_SECONDS` — how long to wait before committing a copy
- `OUTPUT_DIR` / `NOTES_FILE` / `IMAGES_DIR` — where things get saved
- `POLL_INTERVAL` — how often the clipboard is checked

## Windows: run on startup / one-click

Save this as `run_clipcollector.vbs` next to the script to launch with
no console window, then drop a shortcut to it in your Startup folder:

```vbs
CreateObject("Wscript.Shell").Run "pythonw clipcollector.py", 0, False
```

---

# Stage 2 — Browser extension → auto-paste into a live Google Doc

Once you're happy with Stage 1, the natural "stage 2" is a Chrome
extension that skips the local file entirely and streams every copy
straight into a Google Doc you started the extension from. That's a
meaningfully different architecture (browser extension + Google Docs
API + OAuth), worth designing deliberately rather than bolting onto the
script above. Here's the shape it would take:

**Pieces needed:**
1. **Manifest V3 Chrome extension** with a background service worker
   and a popup ("Start capturing into this doc").
2. **Google OAuth** (via `chrome.identity`) so the extension can write
   to Docs on your behalf.
3. **Google Docs API** (`documents.batchUpdate`) to append text/links to
   the doc you selected — this is the part that replaces "append to
   collected_notes.md".
4. **Clipboard capture in the browser**: browsers restrict background
   clipboard polling for privacy, so the practical approach is a
   content-script listener on `copy` events (fires when you hit Ctrl+C
   or right-click → Copy on a page), which reads `event.clipboardData`
   or `navigator.clipboard.readText()`. Images copied from a webpage
   can be grabbed the same way if the copy event carries image data;
   otherwise the extension can capture a screenshot of the selected
   image element and upload that.
5. **3-second debounce**, same idea as Stage 1, implemented via
   `setTimeout` in the background worker before calling the Docs API.

**Rough flow:** you click the extension icon → pick/confirm a Google
Doc → it stores that Doc ID → from then on, any copy on any tab is
caught by a content script → sent to the background worker → after the
delay, inserted at the end of the Doc via `batchUpdate`.


I can build this next — happy to start with the extension skeleton
(manifest, OAuth, popup) once Stage 1 is working well for you and you
confirm you want to move on. It's a good amount of code (manifest,
background worker, content script, OAuth setup in Google Cloud
Console), so I'd rather build it as its own focused pass.

i make this whole program with the help of ai.
