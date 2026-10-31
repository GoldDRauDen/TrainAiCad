"""Admin password (scrypt), admin sessions, per-IP lockout."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time

from .config import ADMIN_SESSION_S, LOCKOUT_FAILS, LOCKOUT_S

N, R, P, DKLEN = 2 ** 14, 8, 1, 32


def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode("utf-8"), salt=salt, n=N, r=R, p=P, dklen=DKLEN)
    return f"scrypt${salt.hex()}${h.hex()}"


def verify_password(pw: str, stored: str | None) -> bool:
    try:
        algo, salt, want = (stored or "").split("$")
    except ValueError:
        return False
    if algo != "scrypt":
        return False
    got = hashlib.scrypt((pw or "").encode("utf-8"), salt=bytes.fromhex(salt), n=N, r=R, p=P, dklen=DKLEN)
    return hmac.compare_digest(got.hex(), want)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Auth:
    def __init__(self, store, clock=time.time):
        self.store, self.clock = store, clock
        self._fails: dict[str, list[float]] = {}   # ip -> [fail count, locked until]
        self._lock = threading.Lock()

    def has_admin_password(self) -> bool:
        return bool(self.store.get_settings().get("admin_hash"))

    def set_admin_password(self, pw: str) -> None:
        if len(pw or "") < 6:
            raise ValueError("Mật khẩu tối thiểu 6 ký tự.")
        self.store.set_settings(admin_hash=hash_password(pw))

    def locked(self, ip: str) -> int:
        with self._lock:
            until = self._fails.get(ip, [0, 0])[1]
        return max(0, int(until - self.clock() + 0.999)) if until > self.clock() else 0

    def login(self, pw: str, ip: str) -> str | None:
        if self.locked(ip):
            return None
        if not verify_password(pw, self.store.get_settings().get("admin_hash")):
            with self._lock:
                rec = self._fails.setdefault(ip, [0, 0])
                rec[0] += 1
                if rec[0] >= LOCKOUT_FAILS:
                    rec[:] = [0, self.clock() + LOCKOUT_S]
            return None
        with self._lock:
            self._fails.pop(ip, None)
        token = secrets.token_urlsafe(32)
        self.store.add_admin_session(_token_hash(token), ip, ADMIN_SESSION_S, now=self.clock())
        return token

    def is_admin(self, token: str | None) -> bool:
        return bool(token) and self.store.admin_session_valid(_token_hash(token), now=self.clock())

    def logout(self, token: str | None) -> None:
        if token:
            self.store.drop_admin_session(_token_hash(token))
