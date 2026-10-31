"""Small OS helpers: keep the PC awake while jobs run, find the LAN address, message boxes. No-ops off Windows."""
from __future__ import annotations

import ctypes
import os
import socket

ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001


def keep_awake(on: bool) -> None:
    if os.name != "nt":
        return
    flags = ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0)
    ctypes.windll.kernel32.SetThreadExecutionState(flags)


def on_active_change(active: int) -> None:
    keep_awake(active > 0)


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))   # no packet is sent; picks the outgoing interface
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def ask_yes_no(title: str, text: str) -> bool:
    if os.name != "nt":
        return True
    MB_YESNO, MB_ICONWARNING, IDYES = 0x04, 0x30, 6
    return ctypes.windll.user32.MessageBoxW(None, text, title, MB_YESNO | MB_ICONWARNING) == IDYES


def show_error(title: str, text: str) -> None:
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)
