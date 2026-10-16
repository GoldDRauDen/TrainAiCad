from pathlib import Path

import ezdxf
import fitz
import pytest


def write_pdf(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), 'Source drawing')
    doc.save(path)
    doc.close()
    return path


def write_dxf(path: Path, length=10):
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.new()
    doc.modelspace().add_line((0, 0), (length, 0))
    doc.saveas(path)
    return path


@pytest.fixture
def store(tmp_path):
    from LuanAppTools.core.store import Store
    return Store(tmp_path / 'app.sqlite3')


@pytest.fixture
def run(store, tmp_path):
    folder = tmp_path / 'jobs' / '520318-15'
    folder.mkdir(parents=True)
    job = store.register_job(folder)
    return store.create_run(job['id'], 'source-one', 'e2a4161')
