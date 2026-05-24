import time
import threading
import tkinter as tk
from tkinter import font as tkfont
from pynput import keyboard, mouse
from pynput.keyboard import Key, Controller
from pynput.mouse import Button as MouseButton
import random
import json
import os
from datetime import datetime
import ctypes  # For SendInput

# ══════════════════════════════════════════════════════════════════════════════
# Bind system
# ══════════════════════════════════════════════════════════════════════════════
SPECIAL_KEYS = {
    "ctrl": Key.ctrl, "left_ctrl": Key.ctrl_l, "right_ctrl": Key.ctrl_r,
    "alt": Key.alt, "left_alt": Key.alt_l, "right_alt": Key.alt_r,
    "shift": Key.shift, "left_shift": Key.shift_l, "right_shift": Key.shift_r,
    "mouse1": MouseButton.left, "mouse2": MouseButton.right,
    "mouse3": MouseButton.middle, "mouse4": MouseButton.x1, "mouse5": MouseButton.x2,
}
SPECIAL_DISPLAY = {
    "ctrl": "CTRL", "left_ctrl": "LCTRL", "right_ctrl": "RCTRL",
    "alt": "ALT", "left_alt": "LALT", "right_alt": "RALT",
    "shift": "SHIFT", "left_shift": "LSHIFT", "right_shift": "RSHIFT",
    "mouse1": "M1", "mouse2": "M2", "mouse3": "M3", "mouse4": "M4", "mouse5": "M5",
}

def key_matches(key, bind_val):
    if bind_val in SPECIAL_KEYS:
        sk = SPECIAL_KEYS[bind_val]
        if isinstance(sk, MouseButton): return key == sk
        if bind_val == "ctrl":  return key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r)
        if bind_val == "alt":   return key in (Key.alt, Key.alt_l, Key.alt_r)
        if bind_val == "shift": return key in (Key.shift, Key.shift_l, Key.shift_r)
        return key == sk
    # Handle F-keys specially
    if bind_val.startswith("f") and len(bind_val) <= 4:
        try:
            f_num = int(bind_val[1:])
            key_name = f"f{f_num}"
            if hasattr(Key, key_name):
                return key == getattr(Key, key_name)
        except:
            pass
    try: return key.char == bind_val
    except AttributeError: return False

def is_special(b): return b in SPECIAL_KEYS
def bind_display(b):
    # Handle F-keys
    if b and b.startswith("f") and len(b) <= 4:
        try:
            f_num = int(b[1:])
            return f"F{f_num}"
        except:
            pass
    return SPECIAL_DISPLAY.get(b, b.upper())

def press_bind(b):
    if input_method == "sendinput":
        sendinput_press(b)
    else:
        if b in SPECIAL_KEYS:
            sk = SPECIAL_KEYS[b]
            if not isinstance(sk, MouseButton): kb.press(sk)
        else: kb.press(b)

def release_bind(b):
    if input_method == "sendinput":
        sendinput_release(b)
    else:
        if b in SPECIAL_KEYS:
            sk = SPECIAL_KEYS[b]
            if not isinstance(sk, MouseButton): kb.release(sk)
        else: kb.release(b)

binds = {
    "edit": "f", "select": "p", "sprint": "v", "pickup": "n",
    "pickup_trigger": "q", "de_trigger": "e",
    "shotgun": "2", "ab_trigger": "t", "ab_place": "0",
    "crouch": "c", "crouch_trigger": "ctrl",
}

# ══════════════════════════════════════════════════════════════════════════════
# SendInput implementation (Windows API)
# ══════════════════════════════════════════════════════════════════════════════
# Virtual key codes for common keys
VK_CODES = {
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46,
    'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C,
    'm': 0x4D, 'n': 0x4E, 'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52,
    's': 0x53, 't': 0x54, 'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58,
    'y': 0x59, 'z': 0x5A,
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    'ctrl': 0x11, 'shift': 0x10, 'alt': 0x12,
}

def sendinput_press(key_char):
    """Press key using SendInput (Windows API)"""
    if key_char.lower() in VK_CODES:
        vk = VK_CODES[key_char.lower()]
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)

def sendinput_release(key_char):
    """Release key using SendInput (Windows API)"""
    if key_char.lower() in VK_CODES:
        vk = VK_CODES[key_char.lower()]
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)  # KEYEVENTF_KEYUP = 2

# ══════════════════════════════════════════════════════════════════════════════
# State
# ══════════════════════════════════════════════════════════════════════════════
kb   = Controller()
lock = threading.Lock()

all_macros_on   = True
macro1_on       = True
select_held     = False
edit_held       = False
delay_ms        = 1
edit_on_release = False
sprint_edit_on  = False  # Sprint editing: press sprint+select once on drag trigger

macro2_on           = True
pickup_trigger_held = False
spam_delay          = 1

macro3_on          = True
de_held            = False
fp_delay           = 1
de_edit_on_release = False  # Double edit: edit on release behaviour
de_sprint_edit_on  = False  # Sprint editing in double edit

shotgun_on    = True
shotgun_delay = 0

macro4_on         = True
auto_build_active = False
ab_delay          = 1

macro5_on           = True
crouch_trigger_held = False
crouch_delay        = 1

# Options
randomization_on = False
current_theme    = "original"
input_method = "sendinput"  # "pynput" or "sendinput" - default to SendInput (faster!)
menu_size = "small"  # "small" (800x450) or "big" (1280x720) - default to small
rgb_mode_on = False  # RGB rainbow cycling mode

# Stream Mode


# Performance Monitor
show_performance_monitor = False

# Special hotkeys
hotkey_hide_show = "f10"
hotkey_panic = "f11"
hotkey_disable_all = "f12"

# Profiles
current_profile = "Default"
profiles = {}

# ══════════════════════════════════════════════════════════════════════════════
# Config Save/Load System
# ══════════════════════════════════════════════════════════════════════════════
CONFIG_FILE = "macro_config.json"

def load_config():
    """Load saved configuration from file"""
    global randomization_on, current_theme, binds, rgb_mode_on
    global macro1_on, macro2_on, macro3_on, macro4_on, macro5_on, shotgun_on
    global delay_ms, spam_delay, fp_delay, shotgun_delay, ab_delay, crouch_delay
    global edit_on_release, sprint_edit_on, de_edit_on_release, de_sprint_edit_on
    global current_profile, profiles
    global input_method, menu_size
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                
                # Load options
                randomization_on = config.get("randomization_on", False)
                current_theme = config.get("current_theme", "original")
                input_method = config.get("input_method", "sendinput")
                menu_size = config.get("menu_size", "small")
                rgb_mode_on = config.get("rgb_mode_on", False)
                
                # Load profiles
                current_profile = config.get("current_profile", "Default")
                profiles = config.get("profiles", {})
                
                # Load macro states
                macro1_on = config.get("macro1_on", True)
                macro2_on = config.get("macro2_on", True)
                macro3_on = config.get("macro3_on", True)
                macro4_on = config.get("macro4_on", True)
                macro5_on = config.get("macro5_on", True)
                shotgun_on = config.get("shotgun_on", True)
                
                # Load delays
                delay_ms = config.get("delay_ms", 1)
                spam_delay = config.get("spam_delay", 1)
                fp_delay = config.get("fp_delay", 1)
                shotgun_delay = config.get("shotgun_delay", 0)
                ab_delay = config.get("ab_delay", 1)
                crouch_delay = config.get("crouch_delay", 1)
                
                # Load other settings
                edit_on_release = config.get("edit_on_release", False)
                sprint_edit_on = config.get("sprint_edit_on", False)
                de_edit_on_release = config.get("de_edit_on_release", False)
                de_sprint_edit_on = config.get("de_sprint_edit_on", False)
                
                # Load keybinds
                saved_binds = config.get("binds", {})
                binds.update(saved_binds)
        except:
            pass  # If loading fails, use defaults

def save_config():
    """Save current configuration to file"""
    config = {
        "randomization_on": randomization_on,
        "current_theme": current_theme,
        "input_method": input_method,
        "menu_size": menu_size,
        "rgb_mode_on": rgb_mode_on,
        "current_profile": current_profile,
        "profiles": profiles,
        "macro1_on": macro1_on,
        "macro2_on": macro2_on,
        "macro3_on": macro3_on,
        "macro4_on": macro4_on,
        "macro5_on": macro5_on,
        "shotgun_on": shotgun_on,
        "delay_ms": delay_ms,
        "spam_delay": spam_delay,
        "fp_delay": fp_delay,
        "shotgun_delay": shotgun_delay,
        "ab_delay": ab_delay,
        "crouch_delay": crouch_delay,
        "edit_on_release": edit_on_release,
        "sprint_edit_on": sprint_edit_on,
        "de_edit_on_release": de_edit_on_release,
        "de_sprint_edit_on": de_sprint_edit_on,
        "binds": binds
    }
    
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except:
        pass  # If saving fails, just continue

# Load config at startup
load_config()

# ══════════════════════════════════════════════════════════════════════════════
# Color Themes
# ══════════════════════════════════════════════════════════════════════════════
THEMES = {
    "original": {
        "BG_MAIN": "#000000", "BG_PANEL": "#0a0a0a", "BG_ITEM": "#0d1117",
        "BG_ITEM2": "#0a0e14", "BG_EXPAND": "#1a2332", "ACCENT": "#0066ff",
        "ACCENT2": "#3388ff", "TEXT": "#ffffff", "TEXT_DIM": "#8b9dc3",
        "TEXT_HINT": "#4a5a7a", "TOGGLE_ON": "#0066ff", "TOGGLE_OFF": "#2a2a2a",
        "BORDER": "#1a3a5a", "WHITE": "#ffffff"
    },
    "blue": {
        "BG_MAIN": "#000000", "BG_PANEL": "#0a0e14", "BG_ITEM": "#0d1520",
        "BG_ITEM2": "#0a1118", "BG_EXPAND": "#1a2f4a", "ACCENT": "#0088ff",
        "ACCENT2": "#33aaff", "TEXT": "#ffffff", "TEXT_DIM": "#89b4f7",
        "TEXT_HINT": "#4a6a9a", "TOGGLE_ON": "#0088ff", "TOGGLE_OFF": "#2a2a2a",
        "BORDER": "#1a4a7a", "WHITE": "#ffffff"
    },
    "green": {
        "BG_MAIN": "#000000", "BG_PANEL": "#0a0e0a", "BG_ITEM": "#0d170d",
        "BG_ITEM2": "#0a140a", "BG_EXPAND": "#1a3a2a", "ACCENT": "#00ff88",
        "ACCENT2": "#33ffaa", "TEXT": "#ffffff", "TEXT_DIM": "#8bd3b4",
        "TEXT_HINT": "#4a7a5a", "TOGGLE_ON": "#00ff88", "TOGGLE_OFF": "#2a2a2a",
        "BORDER": "#1a5a3a", "WHITE": "#ffffff"
    },
    "purple": {
        "BG_MAIN": "#000000", "BG_PANEL": "#0e0a14", "BG_ITEM": "#150d20",
        "BG_ITEM2": "#110a18", "BG_EXPAND": "#2a1a3a", "ACCENT": "#aa66ff",
        "ACCENT2": "#cc88ff", "TEXT": "#ffffff", "TEXT_DIM": "#c89bf7",
        "TEXT_HINT": "#6a4a7a", "TOGGLE_ON": "#aa66ff", "TOGGLE_OFF": "#2a2a2a",
        "BORDER": "#4a1a7a", "WHITE": "#ffffff"
    },
    "red": {
        "BG_MAIN": "#000000", "BG_PANEL": "#140a0a", "BG_ITEM": "#200d0d",
        "BG_ITEM2": "#180a0a", "BG_EXPAND": "#3a1a1a", "ACCENT": "#ff4466",
        "ACCENT2": "#ff6688", "TEXT": "#ffffff", "TEXT_DIM": "#f78b9d",
        "TEXT_HINT": "#7a4a5a", "TOGGLE_ON": "#ff4466", "TOGGLE_OFF": "#2a2a2a",
        "BORDER": "#7a1a2a", "WHITE": "#ffffff"
    }
}

# Current theme colors
COLORS = THEMES[current_theme].copy()

# ══════════════════════════════════════════════════════════════════════════════
# RGB Mode — hue advances in a thread; root.after ticker repaints widgets
# ══════════════════════════════════════════════════════════════════════════════
import colorsys

_rgb_hue  = [0.0]   # 0–360
_rgb_stop = [False]
_rgb_prev_colors = {}   # snapshot of COLORS from last tick, for remapping

def _hsv_to_hex(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h / 360.0, s, v)
    return "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))

def _rgb_advance():
    """Background thread: just advance the hue number."""
    while not _rgb_stop[0]:
        if rgb_mode_on:
            _rgb_hue[0] = (_rgb_hue[0] + 0.5) % 360.0
        time.sleep(0.04)

_rgb_thread = threading.Thread(target=_rgb_advance, daemon=True)
_rgb_thread.start()

def _recolor_all_widgets(old_colors, new_colors):
    """Walk every widget in the app and swap old colour values to new ones."""
    # Build reverse maps: hex_value -> new_hex_value  for bg and fg
    bg_map = {}
    fg_map = {}
    for key in old_colors:
        old_val = old_colors[key]
        new_val = new_colors.get(key, old_val)
        if old_val != new_val:
            bg_map[old_val.lower()] = new_val
            fg_map[old_val.lower()] = new_val

    def walk(widget):
        try:
            wtype = widget.winfo_class()
            # bg
            try:
                cur_bg = widget.cget("bg").lower()
                if cur_bg in bg_map:
                    widget.config(bg=bg_map[cur_bg])
            except Exception:
                pass
            # fg (Labels, Buttons, Scales, Scrollbars)
            if wtype in ("Label", "Button", "Scale", "Checkbutton", "Radiobutton"):
                try:
                    cur_fg = widget.cget("fg").lower()
                    if cur_fg in fg_map:
                        widget.config(fg=fg_map[cur_fg])
                except Exception:
                    pass
            # troughcolor for Scale/Scrollbar
            if wtype in ("Scale", "Scrollbar"):
                try:
                    cur = widget.cget("troughcolor").lower()
                    if cur in bg_map:
                        widget.config(troughcolor=bg_map[cur])
                except Exception:
                    pass
                try:
                    cur = widget.cget("activebackground").lower()
                    if cur in bg_map:
                        widget.config(activebackground=bg_map[cur])
                except Exception:
                    pass
        except Exception:
            pass
        for child in widget.winfo_children():
            walk(child)

    walk(root)

def _rgb_apply_colors():
    """Called every 40ms on main thread. If RGB on: compute new colours,
    walk every widget and swap old→new, then update COLORS dict."""
    global _rgb_prev_colors
    if rgb_mode_on:
        h = _rgb_hue[0]
        new_colors = dict(COLORS)   # start from current
        new_colors["ACCENT"]    = _hsv_to_hex(h,          0.90, 1.00)
        new_colors["ACCENT2"]   = _hsv_to_hex((h+25)%360, 0.75, 1.00)
        new_colors["TOGGLE_ON"] = new_colors["ACCENT"]
        new_colors["BORDER"]    = _hsv_to_hex(h,          0.70, 0.45)
        new_colors["BG_EXPAND"] = _hsv_to_hex(h,          0.50, 0.18)
        new_colors["BG_PANEL"]  = _hsv_to_hex(h,          0.40, 0.10)
        new_colors["BG_ITEM"]   = _hsv_to_hex(h,          0.45, 0.13)
        new_colors["BG_ITEM2"]  = _hsv_to_hex(h,          0.42, 0.11)
        new_colors["BG_MAIN"]   = _hsv_to_hex(h,          0.55, 0.05)

        old_snapshot = dict(COLORS)
        COLORS.update(new_colors)

        _recolor_all_widgets(old_snapshot, new_colors)

        # Redraw all toggle switches (they use canvas, not config)
        for w in _all_toggles:
            try:
                w.config(bg=COLORS["BG_EXPAND"])
                w._draw()
            except Exception:
                pass
        for s in _all_scrollbars:
            try:
                s._redraw()
            except Exception:
                pass

    try:
        root.after(40, _rgb_apply_colors)
    except Exception:
        pass

_all_toggles = []   # all ToggleSwitch instances, for mass redraw
_all_scrollbars = []  # all custom scrollbars, for redraw on theme change

class ModernScrollbar(tk.Canvas):
    def __init__(self, parent, command=None, orient="vertical", width=12, **kwargs):
        super().__init__(parent, width=width, bg=COLORS["BG_MAIN"], highlightthickness=0,
                         bd=0, relief="flat", **kwargs)
        self.command = command
        self.orient = orient
        self._lo = 0.0
        self._hi = 1.0
        self._dragging = False
        self._drag_start_y = 0.0
        self._start_lo = 0.0
        self._hover = False
        self.bind("<Configure>", lambda e: self._redraw())
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        _all_scrollbars.append(self)

    def set(self, lo, hi):
        try:
            self._lo = float(lo)
            self._hi = float(hi)
        except Exception:
            self._lo = float(lo)
            self._hi = float(hi)
        self._redraw()

    def _redraw(self):
        self.delete("all")
        height = max(1, self.winfo_height())
        track_color = COLORS["BG_ITEM2"]
        thumb_color = COLORS["ACCENT2"] if self._hover else COLORS["ACCENT"]
        self.create_rectangle(0, 0, self.winfo_width(), height,
                              fill=track_color, outline="")

        top = max(0.0, min(self._lo, 1.0))
        bottom = max(top, min(self._hi, 1.0))
        thumb_height = max(int((bottom - top) * height), 28)
        y0 = int(top * height)
        y1 = min(max(y0 + thumb_height, y0 + 4), height)
        if y1 > height:
            y1 = height
            y0 = height - thumb_height
        radius = min(8, (y1 - y0) // 2)
        self._thumb_top = y0
        self._thumb_bottom = y1

        self.create_rectangle(2, y0 + radius, self.winfo_width() - 2, y1 - radius,
                              fill=thumb_color, outline="")
        self.create_oval(2, y0, self.winfo_width() - 2, y0 + 2 * radius,
                         fill=thumb_color, outline="")
        self.create_oval(2, y1 - 2 * radius, self.winfo_width() - 2, y1,
                         fill=thumb_color, outline="")

    def _on_click(self, event):
        if self._thumb_top <= event.y <= self._thumb_bottom:
            self._dragging = True
            self._drag_start_y = event.y
            self._start_lo = self._lo
            return
        height = max(1, self.winfo_height())
        thumb_size = max(int((self._hi - self._lo) * height), 28)
        target = (event.y - thumb_size / 2) / height
        target = min(max(target, 0.0), 1.0)
        if self.command:
            self.command("moveto", target)

    def _on_drag(self, event):
        if not self._dragging:
            return
        height = max(1, self.winfo_height())
        delta = event.y - self._drag_start_y
        new_top = self._start_lo + delta / height
        scroll_range = max(1.0 - max(self._hi - self._lo, 0.0), 0.0)
        new_top = min(max(new_top, 0.0), scroll_range)
        if self.command:
            self.command("moveto", new_top)

    def _on_release(self, event):
        self._dragging = False

    def _on_enter(self, event):
        self._hover = True
        self._redraw()

    def _on_leave(self, event):
        self._hover = False
        self._redraw()


def get_random_delay(base_delay):
    """Add 1-6ms random delay if randomization is on"""
    if randomization_on:
        return base_delay + random.randint(1, 6)
    return base_delay

# ══════════════════════════════════════════════════════════════════════════════
# Macro logic
# ══════════════════════════════════════════════════════════════════════════════
def do_press_select():
    global select_held
    actual_delay = get_random_delay(delay_ms)
    time.sleep(actual_delay / 1000.0)
    with lock:
        if edit_held and not select_held:
            press_bind(binds["select"])
            select_held = True

def do_release_select():
    global select_held
    fired = False
    with lock:
        if select_held:
            release_bind(binds["select"])
            select_held = False
            fired = True
    if fired:
        if not edit_on_release:
            press_bind(binds["edit"]); time.sleep(0.008); release_bind(binds["edit"])
        if shotgun_on:
            actual_delay = get_random_delay(shotgun_delay)
            if actual_delay > 0: time.sleep(actual_delay / 1000.0)
            press_bind(binds["shotgun"]); time.sleep(0.01); release_bind(binds["shotgun"])

def do_spam_pickup():
    while pickup_trigger_held and macro2_on:
        press_bind(binds["pickup"]); time.sleep(0.008); release_bind(binds["pickup"])
        actual_delay = get_random_delay(spam_delay)
        time.sleep(actual_delay / 1000.0)

def do_spam_double_edit():
    """
    Double edit spam logic with de_edit_on_release and de_sprint_edit_on.

    Sprint edit ON:  first iteration presses V+P together (once, never again).
    de_edit_on_release OFF  →  loop: f p f  f p f  f p f  ...  (extra f after p)
    de_edit_on_release ON   →  loop: f p  f p  f p  ...        (no extra f)
    """
    sprint_fired = False
    KEY_HOLD = 0.020  # fixed 20ms key hold — balanced speed and reliability
    while de_held and macro3_on:
        actual_delay = get_random_delay(fp_delay)
        gap = actual_delay / 1000.0

        # --- edit press ---
        press_bind(binds["edit"]); time.sleep(KEY_HOLD); release_bind(binds["edit"])
        time.sleep(gap)
        if not (de_held and macro3_on): break

        # --- select press (with optional one-time sprint tap after) ---
        press_bind(binds["select"]); time.sleep(KEY_HOLD); release_bind(binds["select"])
        if de_sprint_edit_on and not sprint_fired:
            time.sleep(KEY_HOLD)
            press_bind(binds["sprint"]); time.sleep(KEY_HOLD); release_bind(binds["sprint"])
            sprint_fired = True
        time.sleep(gap)
        if not (de_held and macro3_on): break

        # --- extra edit press when edit_on_release is OFF ---
        if not de_edit_on_release:
            press_bind(binds["edit"]); time.sleep(KEY_HOLD); release_bind(binds["edit"])
            time.sleep(gap)
            if not (de_held and macro3_on): break

def do_auto_build():
    while auto_build_active and macro4_on:
        press_bind(binds["ab_place"]); time.sleep(0.008); release_bind(binds["ab_place"])
        actual_delay = get_random_delay(ab_delay)
        time.sleep(actual_delay / 1000.0)

def do_crouch_spam():
    while crouch_trigger_held and macro5_on:
        press_bind(binds["crouch"]); time.sleep(0.008); release_bind(binds["crouch"])
        actual_delay = get_random_delay(crouch_delay)
        time.sleep(actual_delay / 1000.0)

# ══════════════════════════════════════════════════════════════════════════════
# Panic shutdown and stream mode
# ══════════════════════════════════════════════════════════════════════════════
def toggle_all_macros():
    """Toggle all macros on/off using the master toggle"""
    global all_macros_on
    all_macros_on = not all_macros_on
    master_tog.set(all_macros_on)
    
    if not all_macros_on:
        # Stop all active macros
        global edit_held, pickup_trigger_held, de_held, crouch_trigger_held, auto_build_active
        edit_held = pickup_trigger_held = de_held = crouch_trigger_held = False
        auto_build_active = False
        do_release_select()
        if ab_spam_lbl[0]: 
            ab_spam_lbl[0].config(text="Spam: INACTIVE", fg=COLORS["TEXT_HINT"])

def panic_shutdown():
    """Immediately disable all macros and close the application"""
    global macro1_on, macro2_on, macro3_on, macro4_on, macro5_on
    global shotgun_on, auto_build_active, edit_held, pickup_trigger_held
    global de_held, crouch_trigger_held, all_macros_on
    all_macros_on = False
    macro1_on = macro2_on = macro3_on = macro4_on = macro5_on = shotgun_on = False
    auto_build_active = False
    edit_held = pickup_trigger_held = de_held = crouch_trigger_held = False
    do_release_select()
    # Force immediate close without saving
    try:
        listener.stop()
        mouse_listener.stop()
    except:
        pass
    root.destroy()
    import sys
    sys.exit(0)



# ══════════════════════════════════════════════════════════════════════════════
# disable_all — called when master toggle is turned off
# ══════════════════════════════════════════════════════════════════════════════
def disable_all():
    """Temporarily disable all macros without changing individual states"""
    global all_macros_on, edit_held, pickup_trigger_held, de_held, crouch_trigger_held, auto_build_active
    all_macros_on = False
    edit_held = pickup_trigger_held = de_held = crouch_trigger_held = False
    auto_build_active = False
    do_release_select()
    if ab_spam_lbl[0]: 
        ab_spam_lbl[0].config(text="Spam: INACTIVE", fg=COLORS["TEXT_HINT"])
    root.after(0, refresh_all_ui)

# ══════════════════════════════════════════════════════════════════════════════
# Keyboard listener
# ══════════════════════════════════════════════════════════════════════════════
waiting_for_bind = [None]

def on_press(key):
    global edit_held, pickup_trigger_held, de_held, crouch_trigger_held

    if waiting_for_bind[0] is not None:
        captured = None
        try:
            if key.char: captured = key.char
        except AttributeError:
            # Check if it's an F-key
            if hasattr(key, 'name') and key.name and key.name.startswith('f'):
                captured = key.name  # f1, f2, f10, etc.
            else:
                for name, sk in SPECIAL_KEYS.items():
                    if isinstance(sk, MouseButton): continue
                    if key_matches(key, name): captured = name; break
        if captured:
            bind_name = waiting_for_bind[0]
            if bind_name.startswith("hotkey_"):
                # Update hotkey
                pass  # Will be handled in finish_rebind
            else:
                binds[bind_name] = captured
            waiting_for_bind[0] = None
            root.after(0, lambda: finish_rebind(bind_name, captured))
        return

    # Check for panic button - immediately quit
    if key_matches(key, hotkey_panic):
        panic_shutdown()
        return
    
    # Check for toggle all macros (F12 default) - toggle on/off
    if key_matches(key, hotkey_disable_all):
        root.after(0, toggle_all_macros)
        return
    
    # Check for hide/show
    if key_matches(key, hotkey_hide_show):
        root.after(0, toggle_window)
        return

    if not all_macros_on: return

    if key_matches(key, binds["edit"]) and macro1_on and not edit_held:
        edit_held = True
        threading.Thread(target=do_press_select, daemon=True).start()
    if key_matches(key, binds["pickup_trigger"]) and macro2_on and not pickup_trigger_held:
        pickup_trigger_held = True
        threading.Thread(target=do_spam_pickup, daemon=True).start()
    if key_matches(key, binds["de_trigger"]) and macro3_on and not de_held:
        de_held = True
        threading.Thread(target=do_spam_double_edit, daemon=True).start()
    if key_matches(key, binds["ab_trigger"]) and macro4_on:
        root.after(0, toggle_auto_build_state)
    if key_matches(key, binds["crouch_trigger"]) and macro5_on and not crouch_trigger_held:
        crouch_trigger_held = True
        threading.Thread(target=do_crouch_spam, daemon=True).start()

def on_release(key):
    global edit_held, pickup_trigger_held, de_held, crouch_trigger_held
    if waiting_for_bind[0] is not None: return
    if key_matches(key, binds["edit"]):
        edit_held = False; do_release_select()
    if key_matches(key, binds["pickup_trigger"]): pickup_trigger_held = False
    if key_matches(key, binds["de_trigger"]): de_held = False
    if key_matches(key, binds["crouch_trigger"]): crouch_trigger_held = False

def on_mouse_click(x, y, button, pressed):
    if waiting_for_bind[0] is not None and pressed:
        for name, sk in SPECIAL_KEYS.items():
            if isinstance(sk, MouseButton) and sk == button:
                bind_name = waiting_for_bind[0]
                binds[bind_name] = name
                waiting_for_bind[0] = None
                root.after(0, lambda: finish_rebind(bind_name, name))
                return

# ══════════════════════════════════════════════════════════════════════════════
# GUI — Enhanced with animations and color themes
# ══════════════════════════════════════════════════════════════════════════════
root = tk.Tk()
root.title("RTweaks")
# Set initial size based on menu_size (default is small 800x600)
if menu_size == "small":
    root.geometry("800x450")
else:
    root.geometry("1280x720")
root.resizable(False, False)
root.configure(bg=COLORS["BG_MAIN"])
root.attributes("-topmost", True)

# Remove default window border to add custom rounded corners
root.overrideredirect(True)

# Create rounded rectangle window shape (Windows)
try:
    import win32gui
    import win32con
    from win32api import RGB
    
    def set_rounded_window():
        hwnd = root.winfo_id()
        # Create rounded region
        region = win32gui.CreateRoundRectRgn(0, 0, 1584, 1092, 30, 30)
        win32gui.SetWindowRgn(hwnd, region, True)
    
    root.after(100, set_rounded_window)
except:
    pass  # If win32 not available, continue without rounded corners

# Dynamic font sizes based on menu_size
if menu_size == "small":
    FONT_TITLE   = tkfont.Font(family="Segoe UI", size=10, weight="bold")
    FONT_TAB     = tkfont.Font(family="Segoe UI", size=9)
    FONT_TAB_ACT = tkfont.Font(family="Segoe UI", size=9, weight="bold")
    FONT_SECTION = tkfont.Font(family="Segoe UI", size=9, weight="bold")
    FONT_LABEL   = tkfont.Font(family="Segoe UI", size=9)
    FONT_SMALL   = tkfont.Font(family="Segoe UI", size=8)
    FONT_BIND    = tkfont.Font(family="Segoe UI", size=8, weight="bold")
else:  # big
    FONT_TITLE   = tkfont.Font(family="Segoe UI", size=14, weight="bold")
    FONT_TAB     = tkfont.Font(family="Segoe UI", size=12)
    FONT_TAB_ACT = tkfont.Font(family="Segoe UI", size=12, weight="bold")
    FONT_SECTION = tkfont.Font(family="Segoe UI", size=13, weight="bold")
    FONT_LABEL   = tkfont.Font(family="Segoe UI", size=12)
    FONT_SMALL   = tkfont.Font(family="Segoe UI", size=10)
    FONT_BIND    = tkfont.Font(family="Segoe UI", size=11, weight="bold")

# Enable font smoothing/antialiasing
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except:
    try:
        from ctypes import windll
        windll.user32.SetProcessDPIAware()  # System DPI aware (fallback)
    except:
        pass  # If fails, continue without DPI awareness

# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT — Aimmy-style: slim title bar + left sidebar + content area
# ══════════════════════════════════════════════════════════════════════════════

def minimize_win(): root.iconify()
def close_win(): on_close()

# Sidebar width
SIDEBAR_W = 56 if menu_size == "small" else 72

# ── Title bar (full width, slim) ───────────────────────────────────────────
titlebar_height = 38 if menu_size == "small" else 52
title_bar = tk.Frame(root, bg=COLORS["BG_PANEL"], height=titlebar_height)
title_bar.pack(fill="x")
title_bar.pack_propagate(False)

# "RT" logo badge on far left
logo_size = 28 if menu_size == "small" else 36
logo_y_off = (titlebar_height - logo_size) // 2
logo_frame = tk.Frame(title_bar, bg=COLORS["ACCENT"], width=logo_size, height=logo_size)
logo_frame.place(x=14, y=logo_y_off)
logo_font_size = 10 if menu_size == "small" else 13
tk.Label(logo_frame, text="R", bg=COLORS["ACCENT"], fg=COLORS["WHITE"],
         font=tkfont.Font(family="Segoe UI", size=logo_font_size, weight="bold")
         ).place(relx=0.5, rely=0.5, anchor="center")

# App name next to logo
title_font_size = 11 if menu_size == "small" else 15
title_label = tk.Label(title_bar, text="RTweaks", bg=COLORS["BG_PANEL"], fg=COLORS["TEXT"],
         font=tkfont.Font(family="Segoe UI", size=title_font_size, weight="bold"))
title_label.place(x=logo_size + 22, y=(titlebar_height - title_font_size - 4) // 2)

# Window control buttons — right side
btn_font_size = 12 if menu_size == "small" else 16
win_w = 800 if menu_size == "small" else 1280
close_btn = tk.Button(title_bar, text="✕", bg=COLORS["BG_PANEL"], fg=COLORS["TEXT_DIM"],
          activebackground="#c0392b", activeforeground=COLORS["WHITE"],
          relief="flat", font=tkfont.Font(family="Segoe UI", size=btn_font_size),
          padx=10, pady=0, cursor="hand2", bd=0, command=close_win)
close_btn.place(x=win_w - 40, y=(titlebar_height - 26) // 2)

min_btn = tk.Button(title_bar, text="─", bg=COLORS["BG_PANEL"], fg=COLORS["TEXT_DIM"],
          activebackground="#1a1a1a", activeforeground=COLORS["TEXT"],
          relief="flat", font=tkfont.Font(family="Segoe UI", size=btn_font_size),
          padx=10, pady=0, cursor="hand2", bd=0, command=minimize_win)
min_btn.place(x=win_w - 80, y=(titlebar_height - 26) // 2)

# Drag window via title bar
def start_drag(e): root._drag_x = e.x; root._drag_y = e.y
def do_drag(e):
    dx = e.x - root._drag_x; dy = e.y - root._drag_y
    root.geometry(f"+{root.winfo_x()+dx}+{root.winfo_y()+dy}")
title_bar.bind("<ButtonPress-1>", start_drag)
title_bar.bind("<B1-Motion>", do_drag)

# Thin separator under title bar
tk.Frame(root, bg=COLORS["BORDER"], height=1).pack(fill="x")

# ── Main area: sidebar + content ───────────────────────────────────────────
main_area = tk.Frame(root, bg=COLORS["BG_MAIN"])
main_area.pack(fill="both", expand=True)

# LEFT SIDEBAR
sidebar = tk.Frame(main_area, bg=COLORS["BG_PANEL"], width=SIDEBAR_W)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

# Thin vertical separator between sidebar and content
tk.Frame(main_area, bg=COLORS["BORDER"], width=1).pack(side="left", fill="y")

# ── Tab system ─────────────────────────────────────────────────────────────
current_tab  = [None]
tab_frames   = {}
tab_labels   = {}
tab_icons    = {}
tab_btns     = {}

# Icons for each tab (Unicode symbols that look clean at small sizes)
TAB_ICON_MAP = {
    "intro":    "⌂",
    "macros":   "⚡",
    "settings": "⚙",
    "keybinds": "⌨",
    "profiles": "☰",
    "discord":  "💬",
}
TAB_LABEL_MAP = {
    "intro":    "Intro",
    "macros":   "Macros",
    "settings": "Settings",
    "keybinds": "Keybinds",
    "profiles": "Profiles",
    "discord":  "Discord",
}

def switch_tab(name):
    if current_tab[0] == name:
        return

    # Deactivate old tab button
    if current_tab[0]:
        old = current_tab[0]
        tab_btns[old].config(bg=COLORS["BG_PANEL"])
        tab_icons[old].config(fg=COLORS["TEXT_DIM"], bg=COLORS["BG_PANEL"])
        tab_labels[old].config(fg=COLORS["TEXT_DIM"], bg=COLORS["BG_PANEL"])
        # Hide old indicator bar
        if hasattr(tab_btns[old], "_ind"):
            tab_btns[old]._ind.config(bg=COLORS["BG_PANEL"])

        # Swap content frames
        def swap():
            tab_frames[old].pack_forget()
            tab_frames[name].pack(fill="both", expand=True)
        root.after(80, swap)
    else:
        tab_frames[name].pack(fill="both", expand=True)

    # Activate new tab button
    tab_btns[name].config(bg=COLORS["BG_MAIN"])
    tab_icons[name].config(fg=COLORS["ACCENT"], bg=COLORS["BG_MAIN"])
    tab_labels[name].config(fg=COLORS["TEXT"], bg=COLORS["BG_MAIN"])
    if hasattr(tab_btns[name], "_ind"):
        tab_btns[name]._ind.config(bg=COLORS["ACCENT"])

    current_tab[0] = name

icon_font_size  = 13 if menu_size == "small" else 17
label_font_size = 6  if menu_size == "small" else 8

def make_sidebar_tab(name):
    """Create a vertical sidebar tab button with icon + label + left accent bar"""
    btn_frame = tk.Frame(sidebar, bg=COLORS["BG_PANEL"], cursor="hand2")
    btn_frame.pack(fill="x")

    # Left accent bar (4px wide, colored when active)
    ind = tk.Frame(btn_frame, bg=COLORS["BG_PANEL"], width=4)
    ind.pack(side="left", fill="y")
    btn_frame._ind = ind

    inner = tk.Frame(btn_frame, bg=COLORS["BG_PANEL"])
    inner.pack(side="left", fill="both", expand=True, pady=7)

    icon_lbl = tk.Label(inner, text=TAB_ICON_MAP[name], bg=COLORS["BG_PANEL"],
                        fg=COLORS["TEXT_DIM"],
                        font=tkfont.Font(family="Segoe UI", size=icon_font_size))
    icon_lbl.pack()

    text_lbl = tk.Label(inner, text=TAB_LABEL_MAP[name], bg=COLORS["BG_PANEL"],
                        fg=COLORS["TEXT_DIM"],
                        font=tkfont.Font(family="Segoe UI", size=label_font_size))
    text_lbl.pack()

    tab_btns[name]   = btn_frame
    tab_icons[name]  = icon_lbl
    tab_labels[name] = text_lbl

    def on_enter(e):
        if current_tab[0] != name:
            btn_frame.config(bg="#0d1117")
            inner.config(bg="#0d1117")
            icon_lbl.config(bg="#0d1117", fg=COLORS["ACCENT2"])
            text_lbl.config(bg="#0d1117", fg=COLORS["ACCENT2"])
    def on_leave(e):
        if current_tab[0] != name:
            btn_frame.config(bg=COLORS["BG_PANEL"])
            inner.config(bg=COLORS["BG_PANEL"])
            icon_lbl.config(bg=COLORS["BG_PANEL"], fg=COLORS["TEXT_DIM"])
            text_lbl.config(bg=COLORS["BG_PANEL"], fg=COLORS["TEXT_DIM"])
    def on_click(e): switch_tab(name)

    for w in [btn_frame, inner, icon_lbl, text_lbl]:
        w.bind("<Button-1>", on_click)
        w.bind("<Enter>", on_enter)
        w.bind("<Leave>", on_leave)

make_sidebar_tab("intro")
make_sidebar_tab("macros")
make_sidebar_tab("settings")
make_sidebar_tab("keybinds")
make_sidebar_tab("profiles")
make_sidebar_tab("discord")

# ── Content area (right of sidebar) ────────────────────────────────────────
body = tk.Frame(main_area, bg=COLORS["BG_MAIN"])
body.pack(side="left", fill="both", expand=True)


# ══════════════════════════════════════════════════════════════════════════════
# INTRODUCTION TAB (Redesigned)
# ══════════════════════════════════════════════════════════════════════════════
intro_frame = tk.Frame(body, bg=COLORS["BG_MAIN"])
tab_frames["intro"] = intro_frame

# Scrollable area
intro_canvas = tk.Canvas(intro_frame, bg=COLORS["BG_MAIN"], highlightthickness=0)
intro_scrollbar = ModernScrollbar(intro_frame, command=intro_canvas.yview, width=10)
intro_canvas.configure(yscrollcommand=intro_scrollbar.set)
intro_scrollbar.pack(side="right", fill="y", padx=(0,4), pady=4)
intro_canvas.pack(side="left", fill="both", expand=True)

intro_content = tk.Frame(intro_canvas, bg=COLORS["BG_MAIN"])
intro_cw = intro_canvas.create_window((0,0), window=intro_content, anchor="nw")
intro_content.bind("<Configure>", lambda e: intro_canvas.configure(scrollregion=intro_canvas.bbox("all")))
intro_canvas.bind("<Configure>", lambda e: intro_canvas.itemconfig(intro_cw, width=e.width))
def on_mousewheel_intro(event):
    intro_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
intro_canvas.bind("<Enter>", lambda e: intro_canvas.bind_all("<MouseWheel>", on_mousewheel_intro))
intro_canvas.bind("<Leave>", lambda e: intro_canvas.unbind_all("<MouseWheel>"))

# --- HERO (unchanged) ---
hero = tk.Frame(intro_content, bg=COLORS["BG_PANEL"])
hero.pack(fill="x")
tk.Frame(hero, bg=COLORS["ACCENT"], height=3).pack(fill="x")
hero_inner = tk.Frame(hero, bg=COLORS["BG_PANEL"])
hero_inner.pack(fill="x", padx=20, pady=14)
hero_left = tk.Frame(hero_inner, bg=COLORS["BG_PANEL"])
hero_left.pack(side="left", fill="y")
title_size = 26 if menu_size == "small" else 34
sub_size   = 9  if menu_size == "small" else 12
tk.Label(hero_left, text="RTweaks", bg=COLORS["BG_PANEL"], fg=COLORS["TEXT"], font=tkfont.Font(family="Segoe UI", size=title_size, weight="bold")).pack(anchor="w")
hero_sub_row = tk.Frame(hero_left, bg=COLORS["BG_PANEL"])
hero_sub_row.pack(anchor="w", pady=(2, 0))
tk.Label(hero_sub_row, text="by ", bg=COLORS["BG_PANEL"], fg=COLORS["TEXT_DIM"], font=tkfont.Font(family="Segoe UI", size=sub_size)).pack(side="left")
tk.Label(hero_sub_row, text="RedBubbleFN", bg=COLORS["BG_PANEL"], fg=COLORS["ACCENT"], font=tkfont.Font(family="Segoe UI", size=sub_size, weight="bold")).pack(side="left")
tk.Frame(hero, bg=COLORS["BORDER"], height=1).pack(fill="x")

# --- Timeline of Features ---
timeline = tk.Frame(intro_content, bg=COLORS["BG_MAIN"])
timeline.pack(fill="x", padx=0, pady=(30, 0))
tk.Label(timeline, text="Key Features", bg=COLORS["BG_MAIN"], fg=COLORS["TEXT"], font=tkfont.Font(family="Segoe UI", size=13 if menu_size=="small" else 18, weight="bold")).pack(anchor="center", pady=(0, 18))

features = [
    ("⚡", "Drag Macro", "Hold your edit bind and it will select the tiles for you. this makes editing much easier and you are gonna be better and faster"),
    ("📦", "Pickup Macro", "Hold your pickup trigger bind to automatically pickup weapons, best for offspawn"),
    ("✏", "Double Edit", "Hold 1 button and it will spam single tile edits for you"),
    ("🔫", "Shotgun Pullout", "after an edit with the drag macro this just pulls out your shotgun for you"),
    ("🏗", "Auto Build", "when you press 1 button it will place builds whenever you go into build mode, this works on toggle"),
    ("🦆", "Crouch Spam", "Hold 1 button and this will spam crouch for you, kinda useless overall"),
]

for i, (icon, title, desc) in enumerate(features):
    row = tk.Frame(timeline, bg=COLORS["BG_MAIN"])
    row.pack(fill="x", padx=0, pady=0)
    # Timeline line
    if i != 0:
        tk.Frame(row, bg=COLORS["BORDER"], width=2, height=18).pack(side="left", padx=(38,0))
    # Icon
    icon_frame = tk.Frame(row, bg=COLORS["BG_MAIN"], width=36, height=36)
    icon_frame.pack_propagate(False)
    icon_frame.pack(side="left", padx=(30, 0), pady=0)
    tk.Label(icon_frame, text=icon, bg=COLORS["BG_MAIN"], fg=COLORS["ACCENT"], font=tkfont.Font(family="Segoe UI", size=18 if menu_size=="small" else 24, weight="bold")).pack(expand=True, fill="both")
    # Content
    content = tk.Frame(row, bg=COLORS["BG_MAIN"])
    content.pack(side="left", padx=(18, 0), pady=0, fill="x", expand=True)
    tk.Label(content, text=title, bg=COLORS["BG_MAIN"], fg=COLORS["TEXT"], font=tkfont.Font(family="Segoe UI", size=12 if menu_size=="small" else 16, weight="bold")).pack(anchor="w")
    tk.Label(content, text=desc, bg=COLORS["BG_MAIN"], fg=COLORS["TEXT_DIM"], font=tkfont.Font(family="Segoe UI", size=9 if menu_size=="small" else 12), wraplength=420 if menu_size=="small" else 600, justify="left").pack(anchor="w", pady=(2, 0))

# --- Quick Start Section ---
quick = tk.Frame(intro_content, bg=COLORS["BG_PANEL"])
quick.pack(fill="x", padx=0, pady=(36, 0))
tk.Label(quick, text="Quick Start", bg=COLORS["BG_PANEL"], fg=COLORS["ACCENT"], font=tkfont.Font(family="Segoe UI", size=12 if menu_size=="small" else 16, weight="bold")).pack(anchor="center", pady=(10, 2))
qs_text = "1. Set your keybinds in the Keybinds tab.\n2. Adjust macro options in the Macros tab.\n3. Use F10 to hide/show, F11 to close, F12 to toggle all.\n4. Join our Discord for support!"
tk.Label(quick, text=qs_text, bg=COLORS["BG_PANEL"], fg=COLORS["TEXT"], font=tkfont.Font(family="Segoe UI", size=9 if menu_size=="small" else 12), justify="center").pack(anchor="center", pady=(0, 12))

# --- Discord Invite ---
discord_invite = tk.Frame(intro_content, bg=COLORS["BG_MAIN"])
discord_invite.pack(fill="x", padx=0, pady=(18, 0))
tk.Label(discord_invite, text="Join the RTweaks Discord for updates & support!", bg=COLORS["BG_MAIN"], fg="#5865F2", font=tkfont.Font(family="Segoe UI", size=11 if menu_size=="small" else 15, weight="bold")).pack(anchor="center")

# Local copy_discord_link for intro tab
def copy_discord_link():
    root.clipboard_clear()
    root.clipboard_append("https://discord.gg/6BhX8TZsvg")
    root.update()
    invite_btn.config(text="✓  Copied!", bg="#2ecc71", activebackground="#27ae60")
    root.after(2000, lambda: invite_btn.config(text="Copy Discord Link", bg="#5865F2", activebackground="#4752C4"))

invite_btn = tk.Button(discord_invite, text="Copy Discord Link", command=copy_discord_link, bg="#5865F2", fg="#ffffff", activebackground="#4752C4", activeforeground="#ffffff", relief="flat", font=tkfont.Font(family="Segoe UI", size=9 if menu_size=="small" else 12, weight="bold"), padx=14, pady=4, cursor="hand2", bd=0)
invite_btn.pack(anchor="center", pady=(8, 0))

# ══════════════════════════════════════════════════════════════════════════════
# Animated Toggle switch widget
# ══════════════════════════════════════════════════════════════════════════════
class ToggleSwitch(tk.Canvas):
    if menu_size == "small":
        W, H, R = 52, 26, 13
    else:
        W, H, R = 70, 34, 17

    def __init__(self, parent, on=True, command=None, **kw):
        super().__init__(parent, width=self.W, height=self.H,
                         bg=parent["bg"], highlightthickness=0, **kw)
        self.on        = on
        self.command   = command
        self.animating = False
        self._knob_x   = None
        _all_toggles.append(self)
        self.bind("<Button-1>", self._click)
        self._draw()

    def _draw(self, cx=None):
        self.delete("all")
        r = self.H // 2
        if cx is None:
            cx = self.W - r - 4 if self.on else r + 4

        color = COLORS["TOGGLE_ON"] if self.on else COLORS["TOGGLE_OFF"]
        # Track — smooth pill shape
        self.create_oval(0, 0, self.H, self.H, fill=color, outline="")
        self.create_oval(self.W-self.H, 0, self.W, self.H, fill=color, outline="")
        self.create_rectangle(r, 0, self.W-r, self.H, fill=color, outline="")

        # Knob — smooth circle with a subtle inner shadow feel
        knob_color = "#ffffff"
        pad = 4
        self.create_oval(cx-r+pad, pad, cx+r-pad, self.H-pad, fill=knob_color, outline="")

    def set(self, val):
        if self.on != val:
            self.on = val
            self._animate_toggle()

    def _animate_toggle(self):
        if self.animating:
            return
        self.animating = True
        steps = 10
        r = self.H // 2
        start_x = self.W - r - 4 if not self.on else r + 4
        end_x   = self.W - r - 4 if self.on     else r + 4

        def animate_step(step):
            if step <= steps:
                progress = step / steps
                # Ease-in-out cubic
                progress = progress * progress * (3 - 2 * progress)
                cx = start_x + (end_x - start_x) * progress
                self._draw(cx)
                self.after(16, lambda: animate_step(step + 1))
            else:
                self.animating = False
        animate_step(0)

    def _click(self, e):
        self.on = not self.on
        self._animate_toggle()
        if self.command:
            self.command(self.on)

# ══════════════════════════════════════════════════════════════════════════════
# MACROS TAB
# ══════════════════════════════════════════════════════════════════════════════
macros_frame = tk.Frame(body, bg=COLORS["BG_MAIN"])
tab_frames["macros"] = macros_frame

# ── Master toggle header bar ───────────────────────────────────────────────
master_hdr = tk.Frame(macros_frame, bg=COLORS["BG_PANEL"])
master_hdr.pack(fill="x")
tk.Frame(master_hdr, bg=COLORS["ACCENT"], width=4).pack(side="left", fill="y")
master_hdr_inner = tk.Frame(master_hdr, bg=COLORS["BG_PANEL"])
master_hdr_inner.pack(side="left", fill="x", expand=True, padx=14, pady=10)
master_title_size = 13 if menu_size == "small" else 17
tk.Label(master_hdr_inner, text="Macros", bg=COLORS["BG_PANEL"], fg=COLORS["TEXT"],
         font=tkfont.Font(family="Segoe UI", size=master_title_size, weight="bold")).pack(anchor="w")
tk.Label(master_hdr_inner, text="Toggle all macros on or off with the master switch",
         bg=COLORS["BG_PANEL"], fg=COLORS["TEXT_DIM"], font=FONT_SMALL).pack(anchor="w")

def on_master_toggle(val):
    global all_macros_on
    all_macros_on = val
    if not val:
        global edit_held, pickup_trigger_held, de_held, crouch_trigger_held, auto_build_active
        edit_held = pickup_trigger_held = de_held = crouch_trigger_held = False
        auto_build_active = False
        do_release_select()
        if ab_spam_lbl[0]:
            ab_spam_lbl[0].config(text="Spam: INACTIVE", fg=COLORS["TEXT_HINT"])

master_tog = ToggleSwitch(master_hdr, on=True, command=on_master_toggle)
master_tog.pack(side="right", padx=16)

tk.Frame(macros_frame, bg=COLORS["BORDER"], height=1).pack(fill="x")

def update_all_toggles():
    """Update all toggle switches to match their state"""
    if drag_tog_ref[0]: drag_tog_ref[0].set(macro1_on)
    if eor_tog_ref[0]: eor_tog_ref[0].set(edit_on_release)
    if shotgun_tog_ref[0]: shotgun_tog_ref[0].set(shotgun_on)
    if pickup_tog_ref[0]: pickup_tog_ref[0].set(macro2_on)
    if de_tog_ref[0]: de_tog_ref[0].set(macro3_on)
    if ab_tog_ref[0]: ab_tog_ref[0].set(macro4_on)
    if crouch_tog_ref[0]: crouch_tog_ref[0].set(macro5_on)
    if rand_tog_ref[0]: rand_tog_ref[0].set(randomization_on)

# Scrollable macro list
scroll_canvas = tk.Canvas(macros_frame, bg=COLORS["BG_MAIN"], highlightthickness=0)
scrollbar     = ModernScrollbar(macros_frame, command=scroll_canvas.yview, width=10)
scroll_canvas.configure(yscrollcommand=scrollbar.set)
scrollbar.pack(side="right", fill="y", padx=(0,4), pady=4)
scroll_canvas.pack(side="left", fill="both", expand=True)

macro_list = tk.Frame(scroll_canvas, bg=COLORS["BG_MAIN"])
cw = scroll_canvas.create_window((0,0), window=macro_list, anchor="nw")

macro_list = tk.Frame(scroll_canvas, bg=COLORS["BG_MAIN"])
cw = scroll_canvas.create_window((0,0), window=macro_list, anchor="nw")

macro_list.bind("<Configure>", lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
scroll_canvas.bind("<Configure>", lambda e: scroll_canvas.itemconfig(cw, width=e.width))

def on_mousewheel_macros(event):
    scroll_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
scroll_canvas.bind("<Enter>", lambda e: scroll_canvas.bind_all("<MouseWheel>", on_mousewheel_macros))
scroll_canvas.bind("<Leave>", lambda e: scroll_canvas.unbind_all("<MouseWheel>"))

def make_section(parent, title, build_fn, default_open=False):
    """Creates a collapsible section with a clean header and expand body"""
    container = tk.Frame(parent, bg=COLORS["BG_MAIN"])
    container.pack(fill="x", pady=3, padx=10)

    header = tk.Frame(container, bg=COLORS["BG_ITEM"], cursor="hand2")
    header.pack(fill="x")

    # Left accent bar
    accent_bar = tk.Frame(header, bg=COLORS["ACCENT"], width=5)
    accent_bar.pack(side="left", fill="y")

    title_lbl = tk.Label(header, text=title, bg=COLORS["BG_ITEM"], fg=COLORS["TEXT"],
                         font=FONT_SECTION, padx=14, pady=11)
    title_lbl.pack(side="left")

    chevron = tk.Label(header, text="▾" if default_open else "▸",
                       bg=COLORS["BG_ITEM"], fg=COLORS["TEXT_HINT"],
                       font=tkfont.Font(family="Segoe UI", size=14, weight="bold"), padx=16)
    chevron.pack(side="right")

    body_outer      = tk.Frame(container, bg=COLORS["BG_MAIN"])
    body_inner_wrap = tk.Frame(body_outer, bg=COLORS["BG_MAIN"], padx=0)
    body_frame      = tk.Frame(body_inner_wrap, bg=COLORS["BG_EXPAND"])
    # Bottom accent line for open state
    body_bottom     = tk.Frame(body_inner_wrap, bg=COLORS["ACCENT"], height=2)

    is_open = [default_open]

    if default_open:
        body_outer.pack(fill="x")
        body_inner_wrap.pack(fill="x")
        body_frame.pack(fill="x")
        build_fn(body_frame)
        body_bottom.pack(fill="x")
        container._built = True
    else:
        container._built = False

    def toggle(e=None):
        if not container._built:
            build_fn(body_frame)
            container._built = True

        if is_open[0]:
            chevron.config(text="▸")
            body_bottom.pack_forget()
            animate_collapse(body_outer, 8)
        else:
            chevron.config(text="▾")
            body_outer.pack(fill="x")
            body_inner_wrap.pack(fill="x")
            body_frame.pack(fill="x")
            body_bottom.pack(fill="x")
            animate_expand(body_frame, 0)
        is_open[0] = not is_open[0]

    def on_enter(e):
        if e.widget in [header, title_lbl, chevron]:
            header.config(bg=COLORS["BG_EXPAND"])
            title_lbl.config(bg=COLORS["BG_EXPAND"], fg=COLORS["ACCENT"])
            chevron.config(bg=COLORS["BG_EXPAND"], fg=COLORS["ACCENT"])
            accent_bar.config(bg=COLORS["ACCENT2"], width=6)

    def on_leave(e):
        if e.widget in [header, title_lbl, chevron]:
            header.config(bg=COLORS["BG_ITEM"])
            title_lbl.config(bg=COLORS["BG_ITEM"], fg=COLORS["TEXT"])
            chevron.config(bg=COLORS["BG_ITEM"], fg=COLORS["TEXT_HINT"])
            accent_bar.config(bg=COLORS["ACCENT"], width=5)

    for w in [header, title_lbl, chevron]:
        w.bind("<Button-1>", toggle)
        w.bind("<Enter>",    on_enter)
        w.bind("<Leave>",    on_leave)

    return body_frame

def animate_expand(frame, step, max_steps=8):
    """Smooth expand animation"""
    if step <= max_steps:
        root.after(20, lambda: animate_expand(frame, step + 1, max_steps))

def animate_collapse(frame, step):
    """Smooth collapse animation"""
    if step > 0:
        root.after(20, lambda: animate_collapse(frame, step - 1))
    else:
        frame.pack_forget()

def row_toggle(parent, label, hint, tog_var, on_change):
    row = tk.Frame(parent, bg=COLORS["BG_EXPAND"], cursor="hand2")
    row.pack(fill="x", padx=10, pady=2)

    strip = tk.Frame(row, bg=COLORS["BG_EXPAND"], width=4)
    strip.pack(side="left", fill="y")

    inner = tk.Frame(row, bg=COLORS["BG_EXPAND"])
    inner.pack(side="left", fill="x", expand=True, padx=(10,6), pady=7)

    lbl_main = tk.Label(inner, text=label, bg=COLORS["BG_EXPAND"], fg=COLORS["TEXT"], font=FONT_LABEL)
    lbl_main.pack(anchor="w")
    if hint:
        lbl_hint = tk.Label(inner, text=hint, bg=COLORS["BG_EXPAND"], fg=COLORS["TEXT_HINT"], font=FONT_SMALL)
        lbl_hint.pack(anchor="w")
    else:
        lbl_hint = None

    t = ToggleSwitch(row, on=tog_var, command=on_change)
    t.pack(side="right", padx=6)

    def _enter(e):
        row.config(bg="#1e2d45")
        strip.config(bg=COLORS["ACCENT"], width=5)
        inner.config(bg="#1e2d45")
        lbl_main.config(bg="#1e2d45", fg=COLORS["ACCENT"])
        if lbl_hint: lbl_hint.config(bg="#1e2d45")
        t.config(bg="#1e2d45")
    def _leave(e):
        row.config(bg=COLORS["BG_EXPAND"])
        strip.config(bg=COLORS["BG_EXPAND"], width=4)
        inner.config(bg=COLORS["BG_EXPAND"])
        lbl_main.config(bg=COLORS["BG_EXPAND"], fg=COLORS["TEXT"])
        if lbl_hint: lbl_hint.config(bg=COLORS["BG_EXPAND"])
        t.config(bg=COLORS["BG_EXPAND"])

    for w in [row, inner, lbl_main] + ([lbl_hint] if lbl_hint else []):
        w.bind("<Enter>", _enter)
        w.bind("<Leave>", _leave)

    return t

def row_slider(parent, label, val, mn, mx, on_change):
    row = tk.Frame(parent, bg=COLORS["BG_EXPAND"])
    row.pack(fill="x", padx=28, pady=(12,16))
    hdr = tk.Frame(row, bg=COLORS["BG_EXPAND"]); hdr.pack(fill="x")
    tk.Label(hdr, text=label, bg=COLORS["BG_EXPAND"], fg=COLORS["TEXT_DIM"], font=FONT_SMALL).pack(side="left")
    val_lbl = tk.Label(hdr, text=f"{val} ms", bg=COLORS["BG_EXPAND"], fg=COLORS["ACCENT"], font=FONT_SMALL)
    val_lbl.pack(side="right")
    def _cb(v, vl=val_lbl):
        vl.config(text=f"{int(float(v))} ms")
        on_change(int(float(v)))
    sl = tk.Scale(row, from_=mn, to=mx, orient="horizontal", command=_cb,
                  bg=COLORS["BG_EXPAND"], fg=COLORS["TEXT_DIM"], troughcolor=COLORS["BG_ITEM"],
                  activebackground=COLORS["ACCENT"], highlightthickness=0, bd=0,
                  sliderlength=32, length=1392, showvalue=False,
                  sliderrelief="flat")
    sl.set(val); sl.pack(fill="x", pady=(8,0))
    rf = tk.Frame(row, bg=COLORS["BG_EXPAND"]); rf.pack(fill="x")
    tk.Label(rf, text=f"{mn} ms", bg=COLORS["BG_EXPAND"], fg=COLORS["TEXT_HINT"], font=FONT_SMALL).pack(side="left")
    return sl, val_lbl

def divider(parent):
    tk.Frame(parent, bg=COLORS["BORDER"], height=2).pack(fill="x", padx=28, pady=8)

# ── Section: Drag Macro ────────────────────────────────────────────────────
drag_tog_ref = [None]
eor_tog_ref  = [None]
shotgun_tog_ref = [None]
pickup_tog_ref = [None]
de_tog_ref = [None]
ab_tog_ref = [None]
crouch_tog_ref = [None]
rand_tog_ref = [None]
delay_sl_ref = [None]
delay_lbl_ref = [None]
shotgun_delay_sl_ref = [None]
shotgun_delay_lbl_ref = [None]
spam_sl_ref = [None]
spam_lbl_ref = [None]
fp_sl_ref = [None]
fp_lbl_ref = [None]
ab_sl_ref = [None]
ab_lbl_ref = [None]
crouch_sl_ref = [None]
crouch_lbl_ref = [None]

def build_drag(p):
    def on_tog(v):
        global macro1_on
        macro1_on = v
        if not v: do_release_select()
        save_config()
    drag_tog_ref[0] = row_toggle(p, "Drag Macro", "Hold edit bind → holds select bind", macro1_on, on_tog)
    divider(p)
    def on_eor(v):
        global edit_on_release
        edit_on_release = v
        save_config()
    eor_tog_ref[0] = row_toggle(p, "Edit on Release", "ON = no extra F press after releasing", edit_on_release, on_eor)
    divider(p)
    delay_sl_ref[0], delay_lbl_ref[0] = row_slider(p, "Delay before select", delay_ms, 1, 50, lambda v: (globals().update(delay_ms=v), save_config()))
    tk.Frame(p, height=12, bg=COLORS["BG_EXPAND"]).pack()

make_section(macro_list, "Drag Macro", build_drag, True)

# ── Section: Shotgun Pullout ───────────────────────────────────────────────
def build_shotgun(p):
    def on_tog(v):
        global shotgun_on; shotgun_on = v
        save_config()
    shotgun_tog_ref[0] = row_toggle(p, "Shotgun Pullout", "Presses shotgun bind when drag is released", shotgun_on, on_tog)
    divider(p)
    shotgun_delay_sl_ref[0], shotgun_delay_lbl_ref[0] = row_slider(p, "Delay before shotgun", shotgun_delay, 0, 50, lambda v: (globals().update(shotgun_delay=v), save_config()))
    tk.Frame(p, height=6, bg=COLORS["BG_EXPAND"]).pack()

make_section(macro_list, "Shotgun Pullout", build_shotgun)

# ── Section: Pickup Macro ──────────────────────────────────────────────────
def build_pickup(p):
    def on_tog(v):
        global macro2_on; macro2_on = v
        save_config()
    pickup_tog_ref[0] = row_toggle(p, "Pickup Macro", "Hold pickup trigger → spams pickup bind", macro2_on, on_tog)
    divider(p)
    spam_sl_ref[0], spam_lbl_ref[0] = row_slider(p, "Spam speed", spam_delay, 1, 50, lambda v: (globals().update(spam_delay=v), save_config()))
    tk.Frame(p, height=6, bg=COLORS["BG_EXPAND"]).pack()

make_section(macro_list, "Pickup Macro", build_pickup)

# ── Section: Double Edit ───────────────────────────────────────────────────
def build_de(p):
    def on_tog(v):
        global macro3_on; macro3_on = v
        save_config()
    de_tog_ref[0] = row_toggle(p, "Double Edit", "Hold DE trigger → spams edit + select bind", macro3_on, on_tog)
    divider(p)
    def on_de_eor(v):
        global de_edit_on_release
        de_edit_on_release = v
        save_config()
    row_toggle(p, "Edit on Release", "OFF: f p f  f p f  |  ON: f p  f p  (no extra F after P)", de_edit_on_release, on_de_eor)
    divider(p)
    def on_de_sprint(v):
        global de_sprint_edit_on
        de_sprint_edit_on = v
        save_config()
    row_toggle(p, "Sprint Editing", "Press sprint bind (V) with the first select only — keeps you sprinting into edit", de_sprint_edit_on, on_de_sprint)
    divider(p)
    fp_sl_ref[0], fp_lbl_ref[0] = row_slider(p, "Spam speed", fp_delay, 1, 50, lambda v: (globals().update(fp_delay=v), save_config()))
    tk.Frame(p, height=6, bg=COLORS["BG_EXPAND"]).pack()

make_section(macro_list, "Double Edit", build_de)

# ── Section: Auto Build ────────────────────────────────────────────────────
ab_spam_lbl = [None]

def build_ab(p):
    def on_tog(v):
        global macro4_on, auto_build_active
        macro4_on = v
        if not v:
            auto_build_active = False
            if ab_spam_lbl[0]: ab_spam_lbl[0].config(text="Spam: INACTIVE", fg=COLORS["TEXT_HINT"])
        save_config()
    ab_tog_ref[0] = row_toggle(p, "Auto Build", "Press trigger once to start/stop spamming place bind", macro4_on, on_tog)
    divider(p)
    status_row = tk.Frame(p, bg=COLORS["BG_EXPAND"]); status_row.pack(fill="x", padx=14, pady=4)
    lbl = tk.Label(status_row, text="Spam: INACTIVE", bg=COLORS["BG_EXPAND"], fg=COLORS["TEXT_HINT"], font=FONT_SMALL)
    lbl.pack(side="left")
    ab_spam_lbl[0] = lbl
    divider(p)
    ab_sl_ref[0], ab_lbl_ref[0] = row_slider(p, "Spam speed", ab_delay, 1, 50, lambda v: (globals().update(ab_delay=v), save_config()))
    tk.Frame(p, height=6, bg=COLORS["BG_EXPAND"]).pack()

make_section(macro_list, "Auto Build", build_ab)

# ── Section: Crouch Spam ───────────────────────────────────────────────────
def build_crouch(p):
    def on_tog(v):
        global macro5_on, crouch_trigger_held
        macro5_on = v
        if not v: crouch_trigger_held = False
        save_config()
    crouch_tog_ref[0] = row_toggle(p, "Crouch Spam", "Hold crouch trigger → spams crouch bind", macro5_on, on_tog)
    divider(p)
    crouch_sl_ref[0], crouch_lbl_ref[0] = row_slider(p, "Spam speed", crouch_delay, 1, 50, lambda v: (globals().update(crouch_delay=v), save_config()))
    tk.Frame(p, height=6, bg=COLORS["BG_EXPAND"]).pack()

make_section(macro_list, "Crouch Spam", build_crouch)

def toggle_auto_build_state():
    global auto_build_active
    if not macro4_on: return
    auto_build_active = not auto_build_active
    if ab_spam_lbl[0]:
        if auto_build_active:
            ab_spam_lbl[0].config(text="Spam: RUNNING", fg=COLORS["ACCENT"])
            threading.Thread(target=do_auto_build, daemon=True).start()
        else:
            ab_spam_lbl[0].config(text="Spam: INACTIVE", fg=COLORS["TEXT_HINT"])

# ══════════════════════════════════════════════════════════════════════════════
# SETTINGS TAB
# ══════════════════════════════════════════════════════════════════════════════
settings_frame = tk.Frame(body, bg=COLORS["BG_MAIN"])
tab_frames["settings"] = settings_frame

# Settings header
settings_hdr = tk.Frame(settings_frame, bg=COLORS["BG_PANEL"])
settings_hdr.pack(fill="x")
tk.Frame(settings_hdr, bg=COLORS["ACCENT"], width=4).pack(side="left", fill="y")
settings_hdr_inner = tk.Frame(settings_hdr, bg=COLORS["BG_PANEL"])
settings_hdr_inner.pack(side="left", fill="x", expand=True, padx=14, pady=10)
tk.Label(settings_hdr_inner, text="Settings", bg=COLORS["BG_PANEL"], fg=COLORS["TEXT"],
         font=tkfont.Font(family="Segoe UI", size=13 if menu_size=="small" else 17, weight="bold")).pack(anchor="w")
tk.Label(settings_hdr_inner, text="Macros, appearance and input options",
         bg=COLORS["BG_PANEL"], fg=COLORS["TEXT_DIM"], font=FONT_SMALL).pack(anchor="w")
tk.Frame(settings_frame, bg=COLORS["BORDER"], height=1).pack(fill="x")

# Scrollable settings list
opt_scroll_canvas = tk.Canvas(settings_frame, bg=COLORS["BG_MAIN"], highlightthickness=0)
opt_scrollbar = ModernScrollbar(settings_frame, command=opt_scroll_canvas.yview, width=10)
opt_scroll_canvas.configure(yscrollcommand=opt_scrollbar.set)
opt_scrollbar.pack(side="right", fill="y", padx=(0,4), pady=4)
opt_scroll_canvas.pack(side="left", fill="both", expand=True)

settings_list = tk.Frame(opt_scroll_canvas, bg=COLORS["BG_MAIN"])
opt_cw = opt_scroll_canvas.create_window((0,0), window=settings_list, anchor="nw")
settings_list.bind("<Configure>", lambda e: opt_scroll_canvas.configure(scrollregion=opt_scroll_canvas.bbox("all")))
opt_scroll_canvas.bind("<Configure>", lambda e: opt_scroll_canvas.itemconfig(opt_cw, width=e.width))

def on_mousewheel_opt(event):
    opt_scroll_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
opt_scroll_canvas.bind("<Enter>", lambda e: opt_scroll_canvas.bind_all("<MouseWheel>", on_mousewheel_opt))
opt_scroll_canvas.bind("<Leave>", lambda e: opt_scroll_canvas.unbind_all("<MouseWheel>"))

# ── helper: section label ──────────────────────────────────────────────────
def settings_section_label(parent, text):
    f = tk.Frame(parent, bg=COLORS["BG_MAIN"])
    f.pack(fill="x", padx=12, pady=(10,2))
    tk.Label(f, text=text.upper(), bg=COLORS["BG_MAIN"], fg=COLORS["TEXT_HINT"],
             font=tkfont.Font(family="Segoe UI", size=7, weight="bold")).pack(anchor="w")
    tk.Frame(parent, bg=COLORS["BORDER"], height=1).pack(fill="x", padx=12)

# ── helper: flat card row (toggle) ────────────────────────────────────────
def settings_toggle_row(parent, label, hint, state, callback):
    card = tk.Frame(parent, bg=COLORS["BG_ITEM"], cursor="hand2")
    card.pack(fill="x", padx=12, pady=2)
    tk.Frame(card, bg=COLORS["BG_ITEM"], width=4).pack(side="left", fill="y")
    inner = tk.Frame(card, bg=COLORS["BG_ITEM"])
    inner.pack(side="left", fill="x", expand=True, padx=10, pady=8)
    lbl = tk.Label(inner, text=label, bg=COLORS["BG_ITEM"], fg=COLORS["TEXT"], font=FONT_LABEL)
    lbl.pack(anchor="w")
    if hint:
        tk.Label(inner, text=hint, bg=COLORS["BG_ITEM"], fg=COLORS["TEXT_HINT"], font=FONT_SMALL).pack(anchor="w")
    t = ToggleSwitch(card, on=state, command=callback)
    t.pack(side="right", padx=10)
    # hover
    accent_strip = tk.Frame(card, bg=COLORS["BG_ITEM"], width=4)
    accent_strip.place(x=0, y=0, relheight=1)
    def _enter(e):
        card.config(bg=COLORS["BG_EXPAND"])
        inner.config(bg=COLORS["BG_EXPAND"])
        lbl.config(bg=COLORS["BG_EXPAND"], fg=COLORS["ACCENT"])
        accent_strip.config(bg=COLORS["ACCENT"])
        t.config(bg=COLORS["BG_EXPAND"])
    def _leave(e):
        card.config(bg=COLORS["BG_ITEM"])
        inner.config(bg=COLORS["BG_ITEM"])
        lbl.config(bg=COLORS["BG_ITEM"], fg=COLORS["TEXT"])
        accent_strip.config(bg=COLORS["BG_ITEM"])
        t.config(bg=COLORS["BG_ITEM"])
    for w in [card, inner, lbl]:
        w.bind("<Enter>", _enter)
        w.bind("<Leave>", _leave)
    return t

# ── helper: pill option selector (replaces blocky buttons) ─────────────────
def settings_pill_selector(parent, options, current, callback):
    """options = list of (key, label, sublabel)"""
    row = tk.Frame(parent, bg=COLORS["BG_ITEM"])
    row.pack(fill="x", padx=12, pady=2)
    inner = tk.Frame(row, bg=COLORS["BG_ITEM"])
    inner.pack(fill="x", padx=12, pady=8)
    pill_refs = {}

    def make_pill(key, label, sublabel, selected):
        pill_w = 110 if menu_size == "small" else 140
        pill_h = 52  if menu_size == "small" else 64
        c = tk.Canvas(inner, width=pill_w, height=pill_h,
                      bg=COLORS["BG_ITEM"], highlightthickness=0, cursor="hand2")
        c.pack(side="left", padx=4)
        r = 8

        def draw(active):
            c.delete("all")
            bg = COLORS["ACCENT"] if active else COLORS["BG_EXPAND"]
            fg = COLORS["WHITE"]  if active else COLORS["TEXT_DIM"]
            # Rounded rect background
            c.create_arc(0, 0, r*2, r*2, start=90, extent=90, fill=bg, outline="")
            c.create_arc(pill_w-r*2, 0, pill_w, r*2, start=0, extent=90, fill=bg, outline="")
            c.create_arc(0, pill_h-r*2, r*2, pill_h, start=180, extent=90, fill=bg, outline="")
            c.create_arc(pill_w-r*2, pill_h-r*2, pill_w, pill_h, start=270, extent=90, fill=bg, outline="")
            c.create_rectangle(r, 0, pill_w-r, pill_h, fill=bg, outline="")
            c.create_rectangle(0, r, pill_w, pill_h-r, fill=bg, outline="")
            c.create_text(pill_w//2, pill_h//2 - 7, text=label, fill=fg,
                          font=tkfont.Font(family="Segoe UI", size=9 if menu_size=="small" else 11, weight="bold"))
            c.create_text(pill_w//2, pill_h//2 + 9, text=sublabel, fill=fg if active else COLORS["TEXT_HINT"],
                          font=tkfont.Font(family="Segoe UI", size=7 if menu_size=="small" else 9))
            c._active = active

        draw(selected)
        pill_refs[key] = (c, draw)

        def click(e):
            callback(key)
            for k, (cc, dd) in pill_refs.items():
                dd(k == key)
        c.bind("<Button-1>", click)
        return c

    for key, label, sublabel in options:
        make_pill(key, label, sublabel, key == current)

# ── SECTION: Macro Options ────────────────────────────────────────────────
settings_section_label(settings_list, "Macro Options")
rand_tog_ref = [None]

def on_rand_toggle(v):
    global randomization_on
    randomization_on = v
    save_config()
rand_tog_ref[0] = settings_toggle_row(settings_list, "Randomization",
    "Adds 1–6ms random delay per macro press — reduces ban risk", randomization_on, on_rand_toggle)

# ── SECTION: Appearance ───────────────────────────────────────────────────
settings_section_label(settings_list, "Appearance")
color_buttons = {}

# RGB toggle
def on_rgb_toggle(v):
    global rgb_mode_on
    rgb_mode_on = v
    if not v:
        old_colors = dict(COLORS)
        COLORS.update(THEMES[current_theme])
        _recolor_all_widgets(old_colors, COLORS)
        # Redraw all toggle switches
        for w in _all_toggles:
            try:
                w.config(bg=COLORS["BG_EXPAND"])
                w._draw()
            except Exception:
                pass
    save_config()
settings_toggle_row(settings_list, "RGB Mode",
    "Slowly cycles all colours through the rainbow in real-time", rgb_mode_on, on_rgb_toggle)

# Theme swatches row
themes_card = tk.Frame(settings_list, bg=COLORS["BG_ITEM"])
themes_card.pack(fill="x", padx=12, pady=2)
themes_inner = tk.Frame(themes_card, bg=COLORS["BG_ITEM"])
themes_inner.pack(fill="x", padx=12, pady=8)
tk.Label(themes_inner, text="Base Color Theme", bg=COLORS["BG_ITEM"],
         fg=COLORS["TEXT_DIM"], font=FONT_SMALL).pack(anchor="w", pady=(0,6))

theme_swatches_row = tk.Frame(themes_inner, bg=COLORS["BG_ITEM"])
theme_swatches_row.pack(anchor="w")

themes_info = [
    ("original", "Original", "#0066ff"),
    ("blue",     "Blue",     "#0088ff"),
    ("green",    "Green",    "#00ff88"),
    ("purple",   "Purple",   "#aa66ff"),
    ("red",      "Red",      "#ff4466"),
]
theme_confirm_lbl = tk.Label(themes_inner, text="", bg=COLORS["BG_ITEM"],
                              fg="#00ff88", font=FONT_SMALL)
theme_confirm_lbl.pack(anchor="w", pady=(4,0))

def select_theme(theme_name):
    global current_theme
    current_theme = theme_name
    if not rgb_mode_on:
        old_colors = dict(COLORS)
        COLORS.update(THEMES[theme_name])
        _recolor_all_widgets(old_colors, COLORS)
        # Redraw all toggle switches
        for w in _all_toggles:
            try:
                w.config(bg=COLORS["BG_EXPAND"])
                w._draw()
            except Exception:
                pass
    save_config()
    for t_name, (dot, lbl) in color_buttons.items():
        dot.config(highlightthickness=3 if t_name == theme_name else 0,
                   highlightbackground=COLORS["WHITE"] if t_name == theme_name else COLORS["BG_ITEM"])
    theme_confirm_lbl.config(text=f"✓  {theme_name.capitalize()} applied")
    themes_inner.after(2000, lambda: theme_confirm_lbl.config(text=""))

for theme_name, label, color in themes_info:
    col = tk.Frame(theme_swatches_row, bg=COLORS["BG_ITEM"])
    col.pack(side="left", padx=4)
    dot_size = 28 if menu_size == "small" else 36
    dot = tk.Frame(col, bg=color, width=dot_size, height=dot_size, cursor="hand2",
                   highlightthickness=3 if theme_name == current_theme else 0,
                   highlightbackground=COLORS["WHITE"])
    dot.pack()
    dot.pack_propagate(False)
    tk.Label(col, text=label, bg=COLORS["BG_ITEM"], fg=COLORS["TEXT_DIM"],
             font=tkfont.Font(family="Segoe UI", size=7)).pack(pady=(2,0))
    dot.bind("<Button-1>", lambda e, t=theme_name: select_theme(t))
    color_buttons[theme_name] = (dot, tk.Label())  # store ref

# ── SECTION: System ───────────────────────────────────────────────────────
settings_section_label(settings_list, "System")

# Input method
input_card = tk.Frame(settings_list, bg=COLORS["BG_ITEM"])
input_card.pack(fill="x", padx=12, pady=2)
input_inner = tk.Frame(input_card, bg=COLORS["BG_ITEM"])
input_inner.pack(fill="x", padx=12, pady=8)
tk.Label(input_inner, text="Input Method", bg=COLORS["BG_ITEM"],
         fg=COLORS["TEXT"], font=FONT_LABEL).pack(anchor="w")
tk.Label(input_inner, text="How macro keypresses are sent to Windows",
         bg=COLORS["BG_ITEM"], fg=COLORS["TEXT_HINT"], font=FONT_SMALL).pack(anchor="w", pady=(0,6))

settings_pill_selector(input_card,
    [("pynput", "pynput", "Cloud Gaming"),
     ("sendinput", "SendInput", "Faster / Safer")],
    input_method,
    lambda v: (globals().update(input_method=v), save_config()))

# Menu size
size_card = tk.Frame(settings_list, bg=COLORS["BG_ITEM"])
size_card.pack(fill="x", padx=12, pady=2)
size_inner = tk.Frame(size_card, bg=COLORS["BG_ITEM"])
size_inner.pack(fill="x", padx=12, pady=8)
tk.Label(size_inner, text="Window Size", bg=COLORS["BG_ITEM"],
         fg=COLORS["TEXT"], font=FONT_LABEL).pack(anchor="w")
tk.Label(size_inner, text="Changes size instantly — no restart needed",
         bg=COLORS["BG_ITEM"], fg=COLORS["TEXT_HINT"], font=FONT_SMALL).pack(anchor="w", pady=(0,6))


def on_size_select(v):
    global menu_size, SIDEBAR_W, titlebar_height, logo_size, logo_y_off
    global FONT_TITLE, FONT_TAB, FONT_TAB_ACT, FONT_SECTION, FONT_LABEL, FONT_SMALL, FONT_BIND
    if v == menu_size:
        return
    menu_size = v
    save_config()

    # Update geometry instantly
    new_w = 800 if v == "small" else 1280
    new_h = 450 if v == "small" else 720
    root.geometry(f"{new_w}x{new_h}")

    # Update sidebar and titlebar sizes
    SIDEBAR_W = 56 if v == "small" else 72
    titlebar_height = 38 if v == "small" else 52
    logo_size = 28 if v == "small" else 36
    logo_y_off = (titlebar_height - logo_size) // 2

    # Update fonts
    if v == "small":
        FONT_TITLE.configure(size=10)
        FONT_TAB.configure(size=9)
        FONT_TAB_ACT.configure(size=9)
        FONT_SECTION.configure(size=9)
        FONT_LABEL.configure(size=9)
        FONT_SMALL.configure(size=8)
        FONT_BIND.configure(size=8)
    else:
        FONT_TITLE.configure(size=14)
        FONT_TAB.configure(size=12)
        FONT_TAB_ACT.configure(size=12)
        FONT_SECTION.configure(size=13)
        FONT_LABEL.configure(size=12)
        FONT_SMALL.configure(size=10)
        FONT_BIND.configure(size=11)

    # Update logo and title
    try:
        logo_frame.config(width=logo_size, height=logo_size)
        logo_frame.place(x=14, y=logo_y_off)
        logo_font_size = 10 if v == "small" else 13
        for widget in logo_frame.winfo_children():
            widget.config(font=tkfont.Font(family="Segoe UI", size=logo_font_size, weight="bold"))
        title_font_size = 11 if v == "small" else 15
        title_label.config(font=tkfont.Font(family="Segoe UI", size=title_font_size, weight="bold"))
        title_label.place(x=logo_size + 22, y=(titlebar_height - title_font_size - 4) // 2)
    except Exception:
        pass

    # Move close/minimize buttons to new positions
    try:
        close_btn.place(x=new_w - 40, y=(titlebar_height - 26) // 2)
        min_btn.place(x=new_w - 80, y=(titlebar_height - 26) // 2)
    except Exception:
        pass

    # Update all toggle switches
    for w in _all_toggles:
        try:
            w.W, w.H, w.R = (52, 26, 13) if v == "small" else (70, 34, 17)
            w.config(width=w.W, height=w.H)
            w._draw()
        except Exception:
            pass

    # Update pill button sizes, slider lengths, and wraplengths
    try:
        # Update all pill buttons
        for pill in bind_pill_btns.values():
            pill.config(width=72 if v == "small" else 100, height=26 if v == "small" else 36)
            pill._draw_pill(pill._normal_bg, pill._normal_fg)
    except Exception:
        pass

    # Update all sliders and wraplengths
    def update_sliders_and_labels(widget):
        for child in widget.winfo_children():
            if isinstance(child, tk.Scale):
                child.config(length=392 if v == "small" else 1392, sliderlength=32 if v == "small" else 32)
            if isinstance(child, tk.Label):
                if hasattr(child, "_wraplength"):  # Custom attribute for wrap labels
                    child.config(wraplength=240 if v == "small" else 360)
            update_sliders_and_labels(child)
    update_sliders_and_labels(root)

    # Update theme dots
    try:
        for t_name, (dot, lbl) in color_buttons.items():
            dot_size = 28 if v == "small" else 36
            dot.config(width=dot_size, height=dot_size)
    except Exception:
        pass

    # Update icon and label font sizes for sidebar
    try:
        icon_font_size = 13 if v == "small" else 17
        label_font_size = 6 if v == "small" else 8
        for icon in tab_icons.values():
            icon.config(font=tkfont.Font(family="Segoe UI", size=icon_font_size))
        for lbl in tab_labels.values():
            lbl.config(font=tkfont.Font(family="Segoe UI", size=label_font_size))
    except Exception:
        pass

    # Update Discord tab font sizes
    try:
        disc_title_size = 16 if v == "small" else 22
        disc_sub_size = 9 if v == "small" else 12
        for widget in disc_content.winfo_children():
            for sub in widget.winfo_children():
                if isinstance(sub, tk.Label):
                    sub.config(font=tkfont.Font(family="Segoe UI", size=disc_title_size))
    except Exception:
        pass

    # Force update/redraw
    root.update_idletasks()

settings_pill_selector(size_card,
    [("small", "Small", "800×450"),
     ("big",   "Big",   "1280×720")],
    menu_size,
    on_size_select)

tk.Frame(settings_list, bg=COLORS["BG_MAIN"], height=10).pack()

# ══════════════════════════════════════════════════════════════════════════════
# refresh_all_ui — called after disable_all
# ══════════════════════════════════════════════════════════════════════════════
def refresh_all_ui():
    master_tog.set(False)
    if ab_spam_lbl[0]: ab_spam_lbl[0].config(text="Spam: INACTIVE", fg=COLORS["TEXT_HINT"])

# ══════════════════════════════════════════════════════════════════════════════
# KEYBINDS TAB
# ══════════════════════════════════════════════════════════════════════════════
keybinds_frame = tk.Frame(body, bg=COLORS["BG_MAIN"])
tab_frames["keybinds"] = keybinds_frame

bind_buttons = {}

# Header
kb_hdr = tk.Frame(keybinds_frame, bg=COLORS["BG_PANEL"])
kb_hdr.pack(fill="x")
tk.Frame(kb_hdr, bg=COLORS["ACCENT"], width=4).pack(side="left", fill="y")
kb_hdr_inner = tk.Frame(kb_hdr, bg=COLORS["BG_PANEL"])
kb_hdr_inner.pack(side="left", fill="x", expand=True, padx=14, pady=10)
tk.Label(kb_hdr_inner, text="Keybinds", bg=COLORS["BG_PANEL"], fg=COLORS["TEXT"],
         font=tkfont.Font(family="Segoe UI", size=13 if menu_size=="small" else 17, weight="bold")).pack(anchor="w")
tk.Label(kb_hdr_inner, text="Click a key badge, then press any key to rebind",
         bg=COLORS["BG_PANEL"], fg=COLORS["TEXT_DIM"], font=FONT_SMALL).pack(anchor="w")
tk.Frame(keybinds_frame, bg=COLORS["BORDER"], height=1).pack(fill="x")

# Scroll area
kb_scroll_canvas = tk.Canvas(keybinds_frame, bg=COLORS["BG_MAIN"], highlightthickness=0)
kb_scrollbar = ModernScrollbar(keybinds_frame, command=kb_scroll_canvas.yview, width=10)
kb_scroll_canvas.configure(yscrollcommand=kb_scrollbar.set)
kb_scrollbar.pack(side="right", fill="y", padx=(0,4), pady=4)
kb_scroll_canvas.pack(side="left", fill="both", expand=True)

kb_inner = tk.Frame(kb_scroll_canvas, bg=COLORS["BG_MAIN"])
kb_cw = kb_scroll_canvas.create_window((0,0), window=kb_inner, anchor="nw")
kb_inner.bind("<Configure>", lambda e: kb_scroll_canvas.configure(scrollregion=kb_scroll_canvas.bbox("all")))
kb_scroll_canvas.bind("<Configure>", lambda e: kb_scroll_canvas.itemconfig(kb_cw, width=e.width))

def on_mousewheel_kb(event):
    kb_scroll_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
kb_scroll_canvas.bind("<Enter>", lambda e: kb_scroll_canvas.bind_all("<MouseWheel>", on_mousewheel_kb))
kb_scroll_canvas.bind("<Leave>", lambda e: kb_scroll_canvas.unbind_all("<MouseWheel>"))

# Pill button factory (reused from earlier)
bind_pill_btns = {}

def make_pill_btn(parent, text, command, width=72, height=26):
    c = tk.Canvas(parent, width=width, height=height,
                  bg=parent["bg"], highlightthickness=0, cursor="hand2")
    r = height // 2
    c._pill_text = text
    c._normal_bg = COLORS["BG_EXPAND"]
    c._hover_bg  = COLORS["ACCENT"]
    c._normal_fg = COLORS["TEXT"]
    c._hover_fg  = COLORS["WHITE"]

    def _draw_pill(bg_col, fg_col):
        c.delete("all")
        c.create_oval(0, 0, height, height, fill=bg_col, outline="")
        c.create_oval(width-height, 0, width, height, fill=bg_col, outline="")
        c.create_rectangle(r, 0, width-r, height, fill=bg_col, outline="")
        c.create_text(width//2, height//2, text=c._pill_text,
                      fill=fg_col, font=FONT_BIND, anchor="center")

    _draw_pill(c._normal_bg, c._normal_fg)
    c._draw_pill = _draw_pill

    c.bind("<Enter>", lambda e: _draw_pill(c._hover_bg, c._hover_fg))
    c.bind("<Leave>", lambda e: _draw_pill(c._normal_bg, c._normal_fg))
    c.bind("<Button-1>", lambda e: command())
    return c

# Section label helper
def kb_section_label(text):
    f = tk.Frame(kb_inner, bg=COLORS["BG_MAIN"])
    f.pack(fill="x", padx=12, pady=(10,2))
    tk.Label(f, text=text.upper(), bg=COLORS["BG_MAIN"], fg=COLORS["TEXT_HINT"],
             font=tkfont.Font(family="Segoe UI", size=7, weight="bold")).pack(anchor="w")
    tk.Frame(kb_inner, bg=COLORS["BORDER"], height=1).pack(fill="x", padx=12)

# Bind row helper
def make_kb_row(key, label, desc, current_val):
    row = tk.Frame(kb_inner, bg=COLORS["BG_ITEM"], cursor="hand2")
    row.pack(fill="x", padx=12, pady=2)
    tk.Frame(row, bg=COLORS["BORDER"], width=3).pack(side="left", fill="y")
    left = tk.Frame(row, bg=COLORS["BG_ITEM"])
    left.pack(side="left", fill="x", expand=True, padx=10, pady=6)
    lbl = tk.Label(left, text=label, bg=COLORS["BG_ITEM"], fg=COLORS["TEXT"], font=FONT_BIND)
    lbl.pack(anchor="w")
    tk.Label(left, text=desc, bg=COLORS["BG_ITEM"], fg=COLORS["TEXT_HINT"], font=FONT_SMALL).pack(anchor="w")
    pill = make_pill_btn(row, current_val, lambda k=key: start_rebind(k))
    pill.pack(side="right", padx=8, pady=6)
    bind_pill_btns[key] = pill
    # hover row highlight
    acc = tk.Frame(row, bg=COLORS["BORDER"], width=3)
    acc.place(x=0, y=0, relheight=1)
    def _enter(e):
        row.config(bg=COLORS["BG_EXPAND"]); left.config(bg=COLORS["BG_EXPAND"])
        lbl.config(bg=COLORS["BG_EXPAND"], fg=COLORS["ACCENT"])
        acc.config(bg=COLORS["ACCENT"])
        pill.config(bg=COLORS["BG_EXPAND"])
    def _leave(e):
        row.config(bg=COLORS["BG_ITEM"]); left.config(bg=COLORS["BG_ITEM"])
        lbl.config(bg=COLORS["BG_ITEM"], fg=COLORS["TEXT"])
        acc.config(bg=COLORS["BORDER"])
        pill.config(bg=COLORS["BG_ITEM"])
        pill._draw_pill(pill._normal_bg, pill._normal_fg)
    for w in [row, left, lbl]:
        w.bind("<Enter>", _enter)
        w.bind("<Leave>", _leave)

# finish_rebind / start_rebind
def finish_rebind(bind_name, new_key):
    global hotkey_hide_show, hotkey_panic, hotkey_disable_all
    waiting_for_bind[0] = None
    if bind_name == "hotkey_hide_show":    hotkey_hide_show = new_key
    elif bind_name == "hotkey_panic":      hotkey_panic = new_key
    elif bind_name == "hotkey_disable_all": hotkey_disable_all = new_key
    if bind_name in bind_pill_btns:
        p = bind_pill_btns[bind_name]
        p._pill_text = bind_display(new_key)
        p._draw_pill(p._normal_bg, p._normal_fg)
    save_config()

def start_rebind(bind_name):
    if waiting_for_bind[0] is not None:
        old = waiting_for_bind[0]
        if old in bind_pill_btns:
            val = binds.get(old, hotkey_hide_show if old=="hotkey_hide_show"
                            else hotkey_panic if old=="hotkey_panic"
                            else hotkey_disable_all)
            p = bind_pill_btns[old]
            p._pill_text = bind_display(val)
            p._draw_pill(p._normal_bg, p._normal_fg)
    waiting_for_bind[0] = bind_name
    if bind_name in bind_pill_btns:
        p = bind_pill_btns[bind_name]
        p._pill_text = "..."
        p._draw_pill(COLORS["ACCENT"], COLORS["WHITE"])

# ── Macro Binds ────────────────────────────────────────────────────────────
kb_section_label("Macro Binds")
macro_bind_rows = [
    ("edit",           "Edit Bind",           "Drag macro trigger"),
    ("select",         "Select Bind",         "Output of drag macro"),
    ("sprint",         "Sprint Bind",         "Used by sprint editing"),
    ("pickup",         "Pickup Bind",         "Output of pickup macro"),
    ("pickup_trigger", "Pickup Trigger",      "Hold to spam pickup"),
    ("de_trigger",     "Double Edit Trigger", "Hold to spam double edit"),
    ("shotgun",        "Shotgun Bind",        "Pressed on drag release"),
    ("ab_trigger",     "Auto Build Trigger",  "Toggles auto build spam"),
    ("ab_place",       "Place Build Bind",    "Spammed by auto build"),
    ("crouch",         "Crouch Bind",         "Spammed by crouch spam"),
    ("crouch_trigger", "Crouch Trigger",      "Hold to spam crouch"),
]
for key, label, desc in macro_bind_rows:
    make_kb_row(key, label, desc, bind_display(binds[key]))

# ── Hotkeys ────────────────────────────────────────────────────────────────
kb_section_label("Hotkeys")
hotkey_bind_rows = [
    ("hotkey_hide_show",   "Hide / Show",       "Toggle menu visibility"),
    ("hotkey_disable_all", "Toggle All Macros", "Turn all macros on/off"),
    ("hotkey_panic",       "Panic Close",       "Instantly close RTweaks"),
]
hotkey_vals = {
    "hotkey_hide_show":   hotkey_hide_show,
    "hotkey_disable_all": hotkey_disable_all,
    "hotkey_panic":       hotkey_panic,
}
for key, label, desc in hotkey_bind_rows:
    make_kb_row(key, label, desc, bind_display(hotkey_vals[key]))

tk.Frame(kb_inner, bg=COLORS["BG_MAIN"], height=10).pack()

# ══════════════════════════════════════════════════════════════════════════════
# PROFILES TAB
# ══════════════════════════════════════════════════════════════════════════════
profiles_frame = tk.Frame(body, bg=COLORS["BG_MAIN"])
tab_frames["profiles"] = profiles_frame

# Header
prof_hdr = tk.Frame(profiles_frame, bg=COLORS["BG_PANEL"])
prof_hdr.pack(fill="x")
tk.Frame(prof_hdr, bg=COLORS["ACCENT"], width=4).pack(side="left", fill="y")
prof_hdr_inner = tk.Frame(prof_hdr, bg=COLORS["BG_PANEL"])
prof_hdr_inner.pack(side="left", fill="x", expand=True, padx=14, pady=10)
tk.Label(prof_hdr_inner, text="Profiles", bg=COLORS["BG_PANEL"], fg=COLORS["TEXT"],
         font=tkfont.Font(family="Segoe UI", size=13 if menu_size=="small" else 17, weight="bold")).pack(anchor="w")
tk.Label(prof_hdr_inner, text="Save and load your macro configurations",
         bg=COLORS["BG_PANEL"], fg=COLORS["TEXT_DIM"], font=FONT_SMALL).pack(anchor="w")

tk.Frame(profiles_frame, bg=COLORS["BORDER"], height=1).pack(fill="x")

# Scrollable content
prof_scroll_canvas = tk.Canvas(profiles_frame, bg=COLORS["BG_MAIN"], highlightthickness=0)
prof_scrollbar     = ModernScrollbar(profiles_frame, command=prof_scroll_canvas.yview, width=10)
prof_scroll_canvas.configure(yscrollcommand=prof_scrollbar.set)
prof_scrollbar.pack(side="right", fill="y", padx=(0,4), pady=4)
prof_scroll_canvas.pack(side="left", fill="both", expand=True)

prof_content = tk.Frame(prof_scroll_canvas, bg=COLORS["BG_MAIN"])
prof_cw = prof_scroll_canvas.create_window((0,0), window=prof_content, anchor="nw")
prof_content.bind("<Configure>", lambda e: prof_scroll_canvas.configure(scrollregion=prof_scroll_canvas.bbox("all")))
prof_scroll_canvas.bind("<Configure>", lambda e: prof_scroll_canvas.itemconfig(prof_cw, width=e.width))

def on_mousewheel_prof(event):
    prof_scroll_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
prof_scroll_canvas.bind("<Enter>", lambda e: prof_scroll_canvas.bind_all("<MouseWheel>", on_mousewheel_prof))
prof_scroll_canvas.bind("<Leave>", lambda e: prof_scroll_canvas.unbind_all("<MouseWheel>"))

# Current profile card
cur_card = tk.Frame(prof_content, bg=COLORS["BG_PANEL"])
cur_card.pack(fill="x", padx=12, pady=(10,4))
tk.Frame(cur_card, bg=COLORS["ACCENT"], width=4).pack(side="left", fill="y")
cur_inner = tk.Frame(cur_card, bg=COLORS["BG_PANEL"])
cur_inner.pack(side="left", fill="x", expand=True, padx=12, pady=8)
tk.Label(cur_inner, text="ACTIVE PROFILE", bg=COLORS["BG_PANEL"], fg=COLORS["TEXT_HINT"],
         font=tkfont.Font(family="Segoe UI", size=7, weight="bold")).pack(anchor="w")
current_prof_label = tk.Label(cur_inner, text=current_profile, bg=COLORS["BG_PANEL"],
                               fg=COLORS["ACCENT"],
                               font=tkfont.Font(family="Segoe UI", size=14 if menu_size=="small" else 18, weight="bold"))
current_prof_label.pack(anchor="w")

# Save button
def save_profile():
    popup = tk.Toplevel(root)
    popup.title("Save Profile")
    popup.geometry("800x360")
    popup.configure(bg=COLORS["BG_PANEL"])
    popup.resizable(False, False)
    popup.attributes("-topmost", True)
    tk.Label(popup, text="Enter Profile Name", bg=COLORS["BG_PANEL"], fg=COLORS["TEXT"],
             font=FONT_TITLE).pack(pady=(60, 20))
    entry = tk.Entry(popup, bg=COLORS["BG_ITEM"], fg=COLORS["TEXT"], font=FONT_LABEL,
                     relief="flat", width=30)
    entry.pack(pady=10, ipady=8)
    entry.insert(0, current_profile)
    entry.select_range(0, tk.END)
    entry.focus()
    def do_save():
        name = entry.get().strip()
        if name:
            profiles[name] = {
                "macro1_on": macro1_on, "macro2_on": macro2_on, "macro3_on": macro3_on,
                "macro4_on": macro4_on, "macro5_on": macro5_on, "shotgun_on": shotgun_on,
                "delay_ms": delay_ms, "spam_delay": spam_delay, "fp_delay": fp_delay,
                "shotgun_delay": shotgun_delay, "ab_delay": ab_delay, "crouch_delay": crouch_delay,
                "edit_on_release": edit_on_release, "randomization_on": randomization_on,
                "binds": binds.copy()
            }
            global current_profile
            current_profile = name
            current_prof_label.config(text=name)
            save_config()
            popup.destroy()
            refresh_profile_list()
    btn_frame = tk.Frame(popup, bg=COLORS["BG_PANEL"])
    btn_frame.pack(pady=15)
    tk.Button(btn_frame, text="Save", command=do_save,
              bg=COLORS["ACCENT"], fg=COLORS["WHITE"], relief="flat",
              font=FONT_LABEL, padx=20, pady=8, cursor="hand2").pack(side="left", padx=5)
    tk.Button(btn_frame, text="Cancel", command=popup.destroy,
              bg=COLORS["BG_ITEM"], fg=COLORS["TEXT"], relief="flat",
              font=FONT_LABEL, padx=20, pady=8, cursor="hand2").pack(side="left", padx=5)
    entry.bind("<Return>", lambda e: do_save())

def load_profile(profile_name):
    if profile_name not in profiles: return
    global current_profile, macro1_on, macro2_on, macro3_on, macro4_on, macro5_on
    global shotgun_on, delay_ms, spam_delay, fp_delay, shotgun_delay, ab_delay, crouch_delay
    global edit_on_release, randomization_on, binds
    profile = profiles[profile_name]
    current_profile = profile_name
    macro1_on = profile.get("macro1_on", True)
    macro2_on = profile.get("macro2_on", True)
    macro3_on = profile.get("macro3_on", True)
    macro4_on = profile.get("macro4_on", True)
    macro5_on = profile.get("macro5_on", True)
    shotgun_on = profile.get("shotgun_on", True)
    delay_ms = profile.get("delay_ms", 5)
    spam_delay = profile.get("spam_delay", 1)
    fp_delay = profile.get("fp_delay", 1)
    shotgun_delay = profile.get("shotgun_delay", 0)
    ab_delay = profile.get("ab_delay", 20)
    crouch_delay = profile.get("crouch_delay", 20)
    edit_on_release = profile.get("edit_on_release", False)
    randomization_on = profile.get("randomization_on", False)
    binds = profile.get("binds", binds).copy()
    # Update bind UI
    for key in binds:
        if key in bind_pill_btns:
            p = bind_pill_btns[key]
            p._pill_text = bind_display(binds[key])
            p._draw_pill(p._normal_bg, p._normal_fg)
    current_prof_label.config(text=profile_name)
    save_config()
    # inline confirmation
    current_prof_label.config(fg="#00ff88")
    prof_content.after(1500, lambda: current_prof_label.config(fg=COLORS["ACCENT"]))
    # Update toggles
    update_all_toggles()
    # Update sliders
    if delay_sl_ref[0]: delay_sl_ref[0].set(delay_ms); delay_lbl_ref[0].config(text=f"{delay_ms} ms")
    if shotgun_delay_sl_ref[0]: shotgun_delay_sl_ref[0].set(shotgun_delay); shotgun_delay_lbl_ref[0].config(text=f"{shotgun_delay} ms")
    if spam_sl_ref[0]: spam_sl_ref[0].set(spam_delay); spam_lbl_ref[0].config(text=f"{spam_delay} ms")
    if fp_sl_ref[0]: fp_sl_ref[0].set(fp_delay); fp_lbl_ref[0].config(text=f"{fp_delay} ms")
    if ab_sl_ref[0]: ab_sl_ref[0].set(ab_delay); ab_lbl_ref[0].config(text=f"{ab_delay} ms")
    if crouch_sl_ref[0]: crouch_sl_ref[0].set(crouch_delay); crouch_lbl_ref[0].config(text=f"{crouch_delay} ms")

def delete_profile(profile_name):
    if profile_name in profiles:
        del profiles[profile_name]
        save_config()
        refresh_profile_list()

# Action buttons row
btn_row = tk.Frame(prof_content, bg=COLORS["BG_MAIN"])
btn_row.pack(fill="x", padx=12, pady=(6,4))

tk.Button(btn_row, text="＋  Save Current", command=save_profile,
          bg=COLORS["ACCENT"], fg=COLORS["WHITE"], activebackground=COLORS["ACCENT2"],
          relief="flat", font=FONT_LABEL, padx=14, pady=6, cursor="hand2", bd=0).pack(side="left", padx=(0,6))

# Saved profiles list
tk.Frame(prof_content, bg=COLORS["BORDER"], height=1).pack(fill="x", padx=12, pady=(4,0))

tk.Label(prof_content, text="SAVED PROFILES", bg=COLORS["BG_MAIN"], fg=COLORS["TEXT_HINT"],
         font=tkfont.Font(family="Segoe UI", size=7, weight="bold")).pack(anchor="w", padx=14, pady=(6,2))

profiles_list_frame = tk.Frame(prof_content, bg=COLORS["BG_MAIN"])
profiles_list_frame.pack(fill="x", padx=12)

def refresh_profile_list():
    for w in profiles_list_frame.winfo_children():
        w.destroy()
    if not profiles:
        tk.Label(profiles_list_frame, text="No saved profiles yet — hit Save Current to create one",
                 bg=COLORS["BG_MAIN"], fg=COLORS["TEXT_HINT"], font=FONT_SMALL).pack(pady=12, anchor="w", padx=4)
    else:
        for prof_name in profiles.keys():
            row = tk.Frame(profiles_list_frame, bg=COLORS["BG_ITEM"])
            row.pack(fill="x", pady=2)
            tk.Frame(row, bg=COLORS["BORDER"], width=3).pack(side="left", fill="y")
            tk.Label(row, text=prof_name, bg=COLORS["BG_ITEM"], fg=COLORS["TEXT"],
                     font=FONT_LABEL).pack(side="left", padx=10, pady=7)
            btns = tk.Frame(row, bg=COLORS["BG_ITEM"])
            btns.pack(side="right", padx=6, pady=6)
            tk.Button(btns, text="Load", command=lambda p=prof_name: load_profile(p),
                      bg=COLORS["ACCENT"], fg=COLORS["WHITE"], relief="flat",
                      font=FONT_SMALL, padx=10, pady=4, cursor="hand2", bd=0).pack(side="left", padx=2)
            tk.Button(btns, text="✕", command=lambda p=prof_name: delete_profile(p),
                      bg="#8b1a1a", fg=COLORS["WHITE"], relief="flat",
                      font=FONT_SMALL, padx=8, pady=4, cursor="hand2", bd=0).pack(side="left", padx=2)

refresh_profile_list()

# Stats/perf containers (kept functional, hidden by default)
stats_section_container = [None]
perf_section_container  = [None]

def rebuild_stats_section():
    if stats_section_container[0]:
        stats_section_container[0].destroy()
        stats_section_container[0] = None

def rebuild_perf_section():
    if perf_section_container[0]:
        perf_section_container[0].destroy()
        perf_section_container[0] = None

rebuild_stats_section()
rebuild_perf_section()

# ══════════════════════════════════════════════════════════════════════════════
# DISCORD TAB
# ══════════════════════════════════════════════════════════════════════════════
discord_frame = tk.Frame(body, bg=COLORS["BG_MAIN"])
tab_frames["discord"] = discord_frame

# Scrollable canvas for discord tab
disc_canvas = tk.Canvas(discord_frame, bg=COLORS["BG_MAIN"], highlightthickness=0)
disc_canvas.pack(fill="both", expand=True)

disc_content = tk.Frame(disc_canvas, bg=COLORS["BG_MAIN"])
disc_cw = disc_canvas.create_window((0, 0), window=disc_content, anchor="nw")
disc_content.bind("<Configure>", lambda e: disc_canvas.configure(scrollregion=disc_canvas.bbox("all")))
disc_canvas.bind("<Configure>", lambda e: disc_canvas.itemconfig(disc_cw, width=e.width))

# ── Discord header banner ──────────────────────────────────────────────────
disc_banner = tk.Frame(disc_content, bg="#5865F2")
disc_banner.pack(fill="x")
disc_banner_inner = tk.Frame(disc_banner, bg="#5865F2")
disc_banner_inner.pack(fill="x", padx=20, pady=16)

disc_title_size = 16 if menu_size == "small" else 22
disc_sub_size   = 9  if menu_size == "small" else 12

disc_top_row = tk.Frame(disc_banner_inner, bg="#5865F2")
disc_top_row.pack(anchor="w")

tk.Label(disc_top_row, text="💬", bg="#5865F2", fg="#ffffff",
         font=tkfont.Font(family="Segoe UI", size=disc_title_size)).pack(side="left", padx=(0,8))
tk.Label(disc_top_row, text="RTweaks Community", bg="#5865F2", fg="#ffffff",
         font=tkfont.Font(family="Segoe UI", size=disc_title_size, weight="bold")).pack(side="left")

tk.Label(disc_banner_inner, text="Join the official server for updates, support, and community",
         bg="#5865F2", fg="#b9bffe",
         font=tkfont.Font(family="Segoe UI", size=disc_sub_size)).pack(anchor="w", pady=(4,0))

# ── Stats row ─────────────────────────────────────────────────────────────
disc_stats_frame = tk.Frame(disc_content, bg=COLORS["BG_PANEL"])
disc_stats_frame.pack(fill="x")

disc_stats_inner = tk.Frame(disc_stats_frame, bg=COLORS["BG_PANEL"])
disc_stats_inner.pack(fill="x", padx=20, pady=12)

stat_items = [
    ("🟢", "Active Community", "Players & devs online daily"),
    ("🔔", "Instant Updates", "First to know about new versions"),
    ("🛠️", "Support", "Get help with setup & bugs"),
]

stat_size = 8 if menu_size == "small" else 11

for icon, title, desc in stat_items:
    stat_row = tk.Frame(disc_stats_inner, bg=COLORS["BG_ITEM"])
    stat_row.pack(fill="x", pady=3)
    tk.Frame(stat_row, bg="#5865F2", width=4).pack(side="left", fill="y")
    stat_inner = tk.Frame(stat_row, bg=COLORS["BG_ITEM"])
    stat_inner.pack(side="left", fill="x", expand=True, padx=10, pady=8)
    tk.Label(stat_inner, text=f"{icon}  {title}", bg=COLORS["BG_ITEM"], fg=COLORS["TEXT"],
             font=tkfont.Font(family="Segoe UI", size=stat_size, weight="bold")).pack(anchor="w")
    tk.Label(stat_inner, text=desc, bg=COLORS["BG_ITEM"], fg=COLORS["TEXT_HINT"],
             font=tkfont.Font(family="Segoe UI", size=stat_size - 1)).pack(anchor="w")

# ── Invite link card ───────────────────────────────────────────────────────
tk.Frame(disc_content, bg=COLORS["BORDER"], height=1).pack(fill="x", padx=20, pady=(12,0))

disc_invite_frame = tk.Frame(disc_content, bg=COLORS["BG_MAIN"])
disc_invite_frame.pack(fill="x", padx=20, pady=12)

disc_link_lbl_size = 8 if menu_size == "small" else 11
tk.Label(disc_invite_frame, text="INVITE LINK", bg=COLORS["BG_MAIN"], fg=COLORS["TEXT_HINT"],
         font=tkfont.Font(family="Segoe UI", size=7, weight="bold")).pack(anchor="w", pady=(0,4))

disc_link_card = tk.Frame(disc_invite_frame, bg=COLORS["BG_ITEM"])
disc_link_card.pack(fill="x")
disc_link_inner = tk.Frame(disc_link_card, bg=COLORS["BG_ITEM"])
disc_link_inner.pack(fill="x", padx=12, pady=10)

tk.Label(disc_link_inner, text="discord.gg/6BhX8TZsvg", bg=COLORS["BG_ITEM"],
         fg=COLORS["ACCENT"],
         font=tkfont.Font(family="Segoe UI", size=disc_link_lbl_size, weight="bold")).pack(side="left")

disc_btn_size = 8 if menu_size == "small" else 11

def copy_discord_link():
    root.clipboard_clear()
    root.clipboard_append("https://discord.gg/6BhX8TZsvg")
    root.update()
    discord_btn.config(text="✓  Copied!", bg="#2ecc71", activebackground="#27ae60")
    root.after(2000, lambda: discord_btn.config(text="Copy Link", bg="#5865F2", activebackground="#4752C4"))

discord_btn = tk.Button(disc_link_inner, text="Copy Link",
                        command=copy_discord_link,
                        bg="#5865F2", fg="#ffffff",
                        activebackground="#4752C4", activeforeground="#ffffff",
                        relief="flat",
                        font=tkfont.Font(family="Segoe UI", size=disc_btn_size, weight="bold"),
                        padx=14, pady=4, cursor="hand2", bd=0)
discord_btn.pack(side="right")

# ── Roles / what to expect ─────────────────────────────────────────────────
tk.Frame(disc_content, bg=COLORS["BORDER"], height=1).pack(fill="x", padx=20, pady=(4,0))

disc_channels_frame = tk.Frame(disc_content, bg=COLORS["BG_MAIN"])
disc_channels_frame.pack(fill="x", padx=20, pady=12)

tk.Label(disc_channels_frame, text="WHAT'S INSIDE", bg=COLORS["BG_MAIN"], fg=COLORS["TEXT_HINT"],
         font=tkfont.Font(family="Segoe UI", size=7, weight="bold")).pack(anchor="w", pady=(0,6))

channels_info = [
    ("#announcements", "New RTweaks releases & changelogs"),
    ("#support",       "Help with setup, binds & bugs"),
    ("#general",       "Chat with other players"),
    ("#vouches",       "See what other players are saying"),
]

ch_size = 8 if menu_size == "small" else 11
for ch_name, ch_desc in channels_info:
    ch_row = tk.Frame(disc_channels_frame, bg=COLORS["BG_PANEL"])
    ch_row.pack(fill="x", pady=2)
    ch_inner = tk.Frame(ch_row, bg=COLORS["BG_PANEL"])
    ch_inner.pack(fill="x", padx=12, pady=6)
    tk.Label(ch_inner, text=ch_name, bg=COLORS["BG_PANEL"], fg="#5865F2",
             font=tkfont.Font(family="Segoe UI", size=ch_size, weight="bold")).pack(side="left")
    tk.Label(ch_inner, text=f" — {ch_desc}", bg=COLORS["BG_PANEL"], fg=COLORS["TEXT_DIM"],
             font=tkfont.Font(family="Segoe UI", size=ch_size)).pack(side="left")

tk.Frame(disc_content, bg=COLORS["BG_MAIN"], height=10).pack()

# ══════════════════════════════════════════════════════════════════════════════
# Show/hide + listeners + cleanup
# ══════════════════════════════════════════════════════════════════════════════
window_visible = True

def toggle_window():
    global window_visible
    if window_visible: root.withdraw(); window_visible = False
    else: root.deiconify(); root.lift(); window_visible = True

listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.daemon = True
listener.start()

mouse_listener = mouse.Listener(on_click=on_mouse_click)
mouse_listener.daemon = True
mouse_listener.start()

def on_close():
    _rgb_stop[0] = True
    save_config()  # Save config before closing
    do_release_select()
    listener.stop()
    mouse_listener.stop()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)



switch_tab("intro")

# Start RGB ticker — runs every 40ms on the main thread via root.after
root.after(200, _rgb_apply_colors)

root.mainloop()