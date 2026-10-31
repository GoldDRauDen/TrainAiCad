import pytest

from luan_app.auth import Auth, hash_password, verify_password


class Clock:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


def test_hash_roundtrip():
    h = hash_password("bí-mật-123")
    assert h.startswith("scrypt$") and verify_password("bí-mật-123", h)
    assert not verify_password("sai", h)


def test_short_password_rejected(store):
    with pytest.raises(ValueError, match="tối thiểu 6"):
        Auth(store).set_admin_password("12345")


def test_login_and_session_expiry(store):
    clk = Clock()
    a = Auth(store, clock=clk)
    assert not a.has_admin_password()
    a.set_admin_password("matkhau1")
    assert a.has_admin_password()
    tok = a.login("matkhau1", "10.0.0.5")
    assert tok and a.is_admin(tok)
    clk.t += 11 * 3600
    assert a.is_admin(tok)
    clk.t += 2 * 3600
    assert not a.is_admin(tok)
    assert not a.is_admin(None)


def test_lockout_after_five_failures(store):
    clk = Clock()
    a = Auth(store, clock=clk)
    a.set_admin_password("matkhau1")
    for _ in range(5):
        assert a.login("sai", "10.0.0.9") is None
    assert a.locked("10.0.0.9") > 0
    assert a.login("matkhau1", "10.0.0.9") is None      # locked even with the right password
    assert a.login("matkhau1", "10.0.0.7")               # other IP unaffected
    clk.t += 301
    assert a.locked("10.0.0.9") == 0
    assert a.login("matkhau1", "10.0.0.9")


def test_logout(store):
    a = Auth(store)
    a.set_admin_password("matkhau1")
    tok = a.login("matkhau1", "ip")
    a.logout(tok)
    assert not a.is_admin(tok)
