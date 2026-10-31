import re
import socket
import threading
import time

import uvicorn

from luan_app import winutil
from luan_app.__main__ import already_running, build, port_free


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def test_second_instance_detects_running(paths):
    port = _free_port()
    assert not already_running(port) and port_free("127.0.0.1", port)
    app, scheduler, _store, _auth = build(paths)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_config=None))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    try:
        for _ in range(100):
            if already_running(port):
                break
            time.sleep(0.05)
        assert already_running(port)
        assert not port_free("127.0.0.1", port)
    finally:
        server.should_exit = True
        t.join(5)
        scheduler.stop()


def test_lan_ip_is_ipv4():
    assert re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", winutil.lan_ip())


def test_keep_awake_is_safe_everywhere():
    winutil.keep_awake(True)
    winutil.keep_awake(False)


def _keys(s):
    it = iter(s)
    return lambda: next(it)


def test_read_masked_echoes_stars_and_handles_backspace():
    from luan_app.__main__ import read_masked
    out = []
    pw = read_masked("Mật khẩu: ", _keys("ab\bcd\r"), out.append)
    assert pw == "acd"
    shown = "".join(out)
    assert shown.startswith("Mật khẩu: ") and shown.count("*") == 4 and shown.endswith("\n")


def test_read_masked_paste_and_ctrl_c():
    import pytest
    from luan_app.__main__ import read_masked
    assert read_masked("", _keys("\x16\r"), lambda s: None, paste=lambda: "matkhau1\r\n") == "matkhau1"
    with pytest.raises(KeyboardInterrupt):
        read_masked("", _keys("a\x03"), lambda s: None)
