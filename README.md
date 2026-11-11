# Circle

A launcher in two halves: a **radial wheel** around your cursor for the six things
you do constantly, and a **Search panel** — press one key, type, and it finds apps,
open windows, files, system settings, actions, sums and the web.

Runs on **Windows 10/11 (64-bit)** and **macOS 11+ (Apple Silicon and Intel)**.

---

## Install

**Windows** — download `Circle-1.3.1-setup.exe` from [Releases](../../releases) and
run it. Per-user install, no admin prompt, into `%LOCALAPPDATA%\Programs\Circle`.

**macOS** — download `Circle-1.3.1-arm64.dmg` (Apple Silicon) or
`Circle-1.3.1-x64.dmg` (Intel), open it, and drag Circle to Applications.

The macOS build is ad-hoc signed, not notarised, so the first launch needs one of:

- right-click Circle in Applications → **Open** → **Open**, or
- `xattr -dr com.apple.quarantine /Applications/Circle.app`

Circle has no Dock icon — it lives in the menu bar.

### macOS permissions

Two system permissions make the whole app work:

| Permission | Why | Where |
| --- | --- | --- |
| **Accessibility** | global shortcuts, switching windows, lock screen | System Settings → Privacy & Security → Accessibility |
| **Screen Recording** | reading window titles so Search can find them | System Settings → Privacy & Security → Screen Recording |

Without Screen Recording, Search still lists windows by app name — just not by title.

## Speed, and what runs when

Circle is built to sit idle and cost nothing, then answer instantly.

| Moment | What happens |
| --- | --- |
| Launch | Tray icon and hotkey listener only — no windows, no scanning, no threads |
| First `Alt+Space` | Search panel built (~12 ms), app list read from a cache on disk (~3 ms) |
| Each keystroke | One pass over the file index — ~8 ms for 25,000 entries, instant for a query you just typed |
| Settings / wheel / switcher | Built the first time you open them, never before |
| Idle | Nothing. No timers, no polling, no background threads |
| Once a day | One HTTPS request to check for an update |

Indexes refresh in the background only while the panel is open, at most weekly,
so a stale index never costs you anything at boot. The file index covers 25,000
entries within five folder levels; both numbers are constants in
`search_providers.py` if you want a wider net.

## Updates

Circle checks GitHub Releases once a day and tells you when a newer version is
out — it never installs anything without a click.

When a release is found you get a panel with its notes, the download size, and a
**Download and install** button. The installer is fetched, verified non-empty,
and then:

- **Windows** — the downloaded `setup.exe` runs silently, closes Circle, replaces
  the files and reopens it.
- **macOS** — a small helper script waits for Circle to quit, mounts the `.dmg`,
  copies `Circle.app` over the old one, clears the quarantine flag and reopens it.

Turn it off in Settings → Updates, or check on demand from the tray menu or the
**Check now** button. A copy running from a git checkout never self-updates; it
tells you to `git pull` instead.

## Shortcuts

| Key | Does |
| --- | --- |
| `Alt + Space` | Open Search (macOS: `Option + Space`) |
| `Ctrl + Space` | Open the wheel — macOS default is `Ctrl + Option + Space`, since `Ctrl + Space` switches input sources |
| `↑` `↓` | Move through results |
| `Enter` | Run the selected result |
| `Shift + Enter` | Reveal it instead of opening |
| `Ctrl + 1…9` | Jump to the nth result |
| `Esc` | Close |

Both shortcuts are editable in Settings. Either can be a middle click.

## What Search finds

- **Apps** — Start Menu and Store apps on Windows; every `.app` in `/Applications`,
  `/System/Applications` and `~/Applications` on macOS.
- **Open windows** — switch to any window by typing part of its title or app name.
- **Files and folders** — indexed from Desktop, Documents, Downloads, Pictures,
  Music, Videos (Movies on macOS) and OneDrive. Add more in `config.json` under
  `search.extra_index_roots`.
- **System settings** — 20 pages on each platform, e.g. "bluetooth", "software
  update", "privacy".
- **Actions** — lock, sleep, screenshot, task manager / Activity Monitor, terminal,
  empty trash, sign out.
- **Maths** — `18*4+2`, `sqrt(2)`, `15% of 240`. Enter copies the answer.
- **The web** — the last row is always a search. `@g`, `@yt`, `@gh`, `@w`, `@npm`,
  `@maps` scope it to a site; a bare URL opens directly.

Ranking combines match quality with how often you pick a result, so the app you
open every morning floats to the top after a few days.

## Run from source

**Windows**

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Windows-only dependencies (`pycaw`, `comtypes`) and macOS-only ones (`pyobjc`)
are marked in `requirements.txt`, so the same command works on both.

Circle keeps its state in `%LOCALAPPDATA%\Circle\` on Windows and
`~/Library/Application Support/Circle/` on macOS:

| File | What it is |
| --- | --- |
| `config.json` | your shortcuts, wheel slots, search settings |
| `usage.json` | how often each result was picked (drives ranking) |
| `file_index.json` | the file index |
| `store_apps.json` | Windows Store app list, refreshed weekly |

## Build the installers

Both are built on real runners in CI — you do not need either OS to cut a release:

```bash
git tag v1.1.1
git push origin v1.1.1
```

`build-installer.yml` produces the Windows `setup.exe` on `windows-latest`;
`build-macos.yml` produces the arm64 and x64 `.dmg` files on `macos-latest` and
`macos-15-intel`. All three attach to the release automatically, and their names
carry the version from `version.py`.

**Locally:**

- Windows — needs [Inno Setup 6](https://jrsoftware.org/isdl.php):
  `powershell -ExecutionPolicy Bypass -File .\build_windows.ps1`
- macOS — needs Xcode command line tools: `./scripts/build_macos.sh`

## Layout

```
main.py               app shell: menu-bar/tray item, hotkeys, wiring
version.py            the app version, and the GitHub repo the updater reads
updater.py            update check, download and install
update_dialog.py      the update prompt
platform_layer.py     every OS call: volume, windows, screenshots, login item
search_window.py      the Search panel
search_providers.py   apps, files, windows, actions, settings, calculator, web
theme.py              design tokens and shared stylesheet
icons.py              drawn icon set (24x24 grid)
wheel_overlay.py      the radial wheel
window_switcher.py    alt-tab style window list
settings_gui.py       settings window
hotkey_manager.py     global shortcuts
action_executor.py    what a wheel slot actually does
scripts/              icon generation, macOS build
installer/            Inno Setup script and version resource
Circle.spec           PyInstaller, Windows
Circle-macos.spec     PyInstaller, macOS .app bundle
```

## Troubleshooting

**A shortcut does nothing.** Another app owns it. On macOS, `Ctrl + Space` is the
input-source switcher and `Cmd + Space` is Spotlight; the wheel defaults to
`Ctrl + Option + Space` for that reason. Change either in Settings.

**macOS: shortcuts or window switching do nothing.** Accessibility permission is
missing — System Settings → Privacy & Security → Accessibility → add Circle.

**macOS: windows show app names but no titles.** Screen Recording permission is
missing. After granting it, restart Circle.

**Search shows no files.** The index builds in the background on first launch and
can take a minute. Delete `file_index.json` from the data folder to force a rebuild.

**Updates say "no build for this platform yet".** A release was published before
its installers finished building. Wait for the workflow to finish, then check
again from the tray menu.

**Store apps are missing (Windows).** They are fetched once with PowerShell and
cached for a week. Delete `store_apps.json` to refresh.
