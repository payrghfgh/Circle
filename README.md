# Circle

A Windows launcher in two halves: a **radial wheel** around your cursor for the six
things you do constantly, and a **Search panel** — press one key, type, and it finds
apps, open windows, files, Windows settings, system actions, sums and the web.

Windows 10 (build 10240) and newer, 64-bit.

---

## Install

Download `Circle-1.1.0-setup.exe` from the [Releases](../../releases) page and run it.

The installer is per-user: no admin prompt, installs to `%LOCALAPPDATA%\Programs\Circle`,
adds Start Menu and (optionally) desktop shortcuts, and can start Circle at sign-in.
Uninstall from Settings → Apps, or the Start Menu folder.

## Shortcuts

| Key | Does |
| --- | --- |
| `Alt + Space` | Open Search |
| `Ctrl + Space` | Open the radial wheel at the cursor |
| `↑` `↓` | Move through results |
| `Enter` | Run the selected result |
| `Shift + Enter` | Reveal it (files, apps) instead of opening |
| `Ctrl + 1…9` | Jump to the nth result |
| `Esc` | Close |

Both shortcuts are editable in Settings. Any shortcut can also be a middle click.

## What Search finds

- **Apps** — Start Menu shortcuts plus Store/UWP apps (via `Get-StartApps`).
- **Open windows** — switch to any window by typing part of its title.
- **Files and folders** — indexed from Desktop, Documents, Downloads, Pictures,
  Music, Videos and OneDrive. Extra roots can be added in `config.json`
  (`search.extra_index_roots`).
- **Windows settings** — 20 pages, e.g. "bluetooth", "windows update", "privacy".
- **Actions** — lock, sleep, screenshot, task manager, terminal, empty recycle bin.
- **Maths** — `18*4+2`, `sqrt(2)`, `15% of 240`. Enter copies the answer.
- **The web** — the last row is always a search. `@g`, `@yt`, `@gh`, `@w`, `@npm`,
  `@maps` scope it to a site; a bare URL opens directly.

Results are ranked by how well the text matches and by what you actually pick, so
the app you open every morning floats to the top after a few days.

## Run from source

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

or double-click `run_circle.bat`.

Python 3.10+ on Windows. Circle keeps its caches and your config in
`%LOCALAPPDATA%\Circle\`:

| File | What it is |
| --- | --- |
| `config.json` | your shortcuts, wheel slots, search settings |
| `usage.json` | how often each result was picked (drives ranking) |
| `file_index.json` | the file index |
| `store_apps.json` | Store app list, refreshed weekly |

## Build the installer

**On GitHub (recommended).** Push a tag and the workflow builds everything on a
real Windows runner:

```powershell
git tag v1.1.0
git push origin v1.1.0
```

The installer lands in the workflow run as an artifact and is attached to the release.

**Locally.** You need [Inno Setup 6](https://jrsoftware.org/isdl.php) installed:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

That runs the compile check, freezes the app with PyInstaller (`dist\Circle\`) and
compiles `installer\Circle.iss` into `installer\output\Circle-1.1.0-setup.exe`.

The installer is unsigned, so Windows SmartScreen will show "Windows protected your
PC" on first run — *More info → Run anyway*. Code-signing needs a certificate that
this repo does not ship.

## Layout

```
main.py               app shell: tray, hotkeys, wiring
search_window.py      the Search panel
search_providers.py   apps, files, windows, actions, settings, calculator, web
theme.py              design tokens and shared stylesheet
icons.py              drawn icon set (24x24 grid)
wheel_overlay.py      the radial wheel
window_switcher.py    alt-tab style window list
settings_gui.py       settings window
hotkey_manager.py     global shortcuts
action_executor.py    what a wheel slot actually does
installer/            Inno Setup script and version resource
```

## Troubleshooting

**A shortcut does nothing.** Another app owns it — `Alt + Space` is also the window
menu. Change it in Settings → Search shortcut.

**Search shows no files.** The index builds in the background on first launch and
can take a minute. Check that the folders exist; delete
`%LOCALAPPDATA%\Circle\file_index.json` to force a rebuild.

**Store apps are missing.** They are fetched once with PowerShell and cached for a
week. Delete `%LOCALAPPDATA%\Circle\store_apps.json` to refresh.
