"""System-tray icon: Mở app / Copy link LAN / Thoát (asks before cancelling running jobs)."""
from __future__ import annotations

import subprocess
import webbrowser

from PIL import Image, ImageDraw

from . import winutil


def _image() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 63, 63), radius=14, fill=(16, 24, 40, 255))
    for dy in (0, 12, 22):
        d.line([(14, 26 + dy), (32, 35 + dy), (50, 26 + dy)], fill="white", width=4, joint="curve")
    d.polygon([(32, 10), (50, 20), (32, 30), (14, 20)], outline="white", width=4)
    return img


def run_tray(local_url: str, lan_url: str, scheduler, on_quit) -> None:
    import pystray  # imported here: needs a desktop session

    def open_app(_icon=None, _item=None):
        webbrowser.open(local_url)

    def copy_link(_icon=None, _item=None):
        subprocess.run(["clip"], input=lan_url.encode("utf-16-le"), check=False,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def quit_app(icon, _item=None):
        runs = scheduler.store.active_runs()
        running = [r for r in runs if r["status"] != "QUEUED"]
        if running:
            jobs = ", ".join(r["job"] for r in running)
            if not winutil.ask_yes_no("Luan App", f"Đang chạy {len(running)} job ({jobs}). Thoát sẽ hủy chúng. Chắc chắn?"):
                return
        on_quit()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Mở app", open_app, default=True),
        pystray.MenuItem(f"Copy link LAN ({lan_url})", copy_link),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Thoát", quit_app),
    )
    pystray.Icon("luan_app", _image(), "Luan App — CAD jobs", menu).run()
