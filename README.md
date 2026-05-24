# MHTWEAKS (RTweaks)

A Fortnite macro tool with a modern dark-themed UI built in Python/Tkinter.

## Features

- **Drag Macro** — Hold your edit bind and it auto-selects tiles for faster editing
- **Pickup Macro** — Hold pickup trigger to auto-spam pickup (great for off-spawn)
- **Double Edit** — Hold one button to spam single-tile edits
- **Shotgun Pullout** — Auto-pulls shotgun after a drag macro edit
- **Auto Build** — Toggle to auto-spam place builds in build mode
- **Crouch Spam** — Hold one button to spam crouch

## UI Highlights

- Sleek dark theme with 5 color presets (Original, Blue, Green, Purple, Red)
- RGB rainbow cycling mode
- Animated toggle switches and collapsible macro sections
- Sidebar navigation with tabs: Intro, Macros, Settings, Keybinds, Profiles, Discord
- Custom modern scrollbars
- Small (800x450) and Big (1280x720) window modes
- Profile system to save/load macro configurations
- Draggable borderless window with rounded corners (Windows)

## Input Methods

- **SendInput** (default) — Uses Windows API `keybd_event` for faster, safer input
- **pynput** — Alternative method, works with cloud gaming

## Hotkeys

| Key  | Action              |
|------|---------------------|
| F10  | Hide / Show window  |
| F11  | Panic close         |
| F12  | Toggle all macros   |

All hotkeys are rebindable in the Keybinds tab.

## Requirements

- Python 3.8+
- Windows OS
- Dependencies: `pynput`, `pywin32` (optional, for rounded corners)

## Installation

```bash
pip install -r requirements.txt
python rtweaks.py
```

## Configuration

Settings are auto-saved to `macro_config.json` in the working directory. This includes keybinds, delays, theme, macro states, and profiles.

## Discord

Join the RTweaks community: [discord.gg/6BhX8TZsvg](https://discord.gg/6BhX8TZsvg)
