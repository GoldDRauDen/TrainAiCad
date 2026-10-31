import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "static"


def test_index_uses_only_local_assets():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert not re.search(r'(src|href)="https?://', html)
    for ref in re.findall(r'(?:src|href)="([^"#]+)"', html):
        assert (STATIC / ref).is_file(), ref
    css = (STATIC / "fonts.css").read_text(encoding="utf-8")
    for ref in re.findall(r"url\('([^']+)'\)", css):
        assert (STATIC / ref).is_file(), ref


def test_ids_used_by_js_exist():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    ids = set(re.findall(r'id="([\w-]+)"', html)) | set(re.findall(r'id="([\w-]+)"', js))  # JS templates create some
    used = set(re.findall(r"\$\('#([\w-]+)'\)", js))
    assert used and used <= ids, used - ids


def test_theme_blocks():
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    assert ':root[data-theme="dark"]' in css and "prefers-color-scheme: dark" in css
    assert "prefers-reduced-motion" in css
