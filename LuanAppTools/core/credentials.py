"""Per-user encrypted storage for provider API credentials on Windows."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from pathlib import Path
import tempfile


class _DataBlob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_byte))]


class CredentialStore:
    """Store API keys as DPAPI blobs bound to the current Windows user."""

    def __init__(self, data_dir: Path):
        self.directory = Path(data_dir).resolve() / "credentials"

    @staticmethod
    def _crypt(data: bytes, *, protect: bool) -> bytes:
        if os.name != "nt":
            raise RuntimeError("Secure provider credentials require Windows DPAPI")
        crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        source_buffer = ctypes.create_string_buffer(data)
        source = _DataBlob(
            len(data), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte))
        )
        result = _DataBlob()
        description = wintypes.LPWSTR()
        operation = (
            crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
        )
        if protect:
            operation.argtypes = [
                ctypes.POINTER(_DataBlob),
                wintypes.LPCWSTR,
                ctypes.POINTER(_DataBlob),
                ctypes.c_void_p,
                ctypes.c_void_p,
                wintypes.DWORD,
                ctypes.POINTER(_DataBlob),
            ]
            arguments = (
                ctypes.byref(source),
                "LuanAppTools provider credential",
                None,
                None,
                None,
                0x1,  # CRYPTPROTECT_UI_FORBIDDEN
                ctypes.byref(result),
            )
        else:
            operation.argtypes = [
                ctypes.POINTER(_DataBlob),
                ctypes.POINTER(wintypes.LPWSTR),
                ctypes.POINTER(_DataBlob),
                ctypes.c_void_p,
                ctypes.c_void_p,
                wintypes.DWORD,
                ctypes.POINTER(_DataBlob),
            ]
            arguments = (
                ctypes.byref(source),
                ctypes.byref(description),
                None,
                None,
                None,
                0x1,
                ctypes.byref(result),
            )
        operation.restype = wintypes.BOOL
        try:
            if not operation(*arguments):
                raise OSError(ctypes.get_last_error(), "Windows credential protection failed")
            return ctypes.string_at(result.data, result.size)
        finally:
            if result.data:
                kernel32.LocalFree(result.data)
            if description:
                kernel32.LocalFree(description)

    def is_set(self, name: str) -> bool:
        return self._path(name).is_file()

    def get(self, name: str) -> str | None:
        path = self._path(name)
        if not path.is_file():
            return None
        try:
            return self._crypt(path.read_bytes(), protect=False).decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise RuntimeError("Saved provider credential could not be unlocked") from exc

    def set(self, name: str, value: str) -> None:
        if not isinstance(value, str) or not value or "\r" in value or "\n" in value:
            raise ValueError("Credential must be a non-empty single-line value")
        self.directory.mkdir(parents=True, exist_ok=True)
        protected = self._crypt(value.encode("utf-8"), protect=True)
        fd, temporary = tempfile.mkstemp(prefix=".credential-", dir=self.directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(protected)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path(name))
        finally:
            Path(temporary).unlink(missing_ok=True)

    def delete(self, name: str) -> None:
        self._path(name).unlink(missing_ok=True)

    def _path(self, name: str) -> Path:
        if name not in {"openai", "custom"}:
            raise ValueError("Unknown credential slot")
        return self.directory / f"{name}.dpapi"
