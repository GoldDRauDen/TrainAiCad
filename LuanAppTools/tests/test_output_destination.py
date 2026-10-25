"""The combined DXF goes to the job's input folder by default, or to a destination chosen in the app."""
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from .conftest import write_dxf
from LuanAppTools.core.publisher import Publisher
from LuanAppTools.core.settings import Settings
from LuanAppTools.service.api import create_app
from LuanAppTools.service.controller import ApplicationService
from LuanAppTools.tests.test_controller import sources
from LuanAppTools.tests.test_pipeline import ScriptedRunner, synthetic_part

ROOT = Path(__file__).resolve().parents[2]
NAME = '520318-15_ALL.dxf'


def test_combined_dxf_goes_to_the_configured_destination(store, run, tmp_path):
    lease = store.claim_run(run['id'], 'worker')
    stage = write_dxf(tmp_path / 'stage.dxf')
    out = tmp_path / 'delivered'
    result = Publisher(store, tmp_path / 'history').publish(
        run['id'], lease, 'source-one', {NAME: stage}, combined_destination=out)
    folder = store.get_job(run['job_id'])['folder']
    assert (out / NAME).is_file() and not (folder / NAME).exists()
    assert [Path(p) for p in result['files']] == [(out / NAME).resolve()]
    assert [Path(o['path']) for o in store.outputs(run['id'])] == [(out / NAME).resolve()]


def test_unowned_file_in_the_destination_is_never_overwritten(store, run, tmp_path):
    out = tmp_path / 'delivered'
    out.mkdir()
    (out / NAME).write_bytes(b'customer owned')
    lease = store.claim_run(run['id'], 'worker')
    with pytest.raises(FileExistsError):
        Publisher(store, tmp_path / 'history').publish(
            run['id'], lease, 'source-one', {NAME: write_dxf(tmp_path / 'stage.dxf')}, combined_destination=out)
    assert (out / NAME).read_bytes() == b'customer owned'


def test_symlinked_destination_is_rejected(store, run, tmp_path):
    real = tmp_path / 'real'
    real.mkdir()
    link = tmp_path / 'link'
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip('symlinks need a privilege on this machine')
    lease = store.claim_run(run['id'], 'worker')
    with pytest.raises(ValueError, match='Symlink'):
        Publisher(store, tmp_path / 'history').publish(
            run['id'], lease, 'source-one', {NAME: write_dxf(tmp_path / 'stage.dxf')}, combined_destination=link)
    assert list(real.iterdir()) == []


def test_default_destination_is_the_job_folder(store, run, tmp_path):
    lease = store.claim_run(run['id'], 'worker')
    Publisher(store, tmp_path / 'history').publish(run['id'], lease, 'source-one', {NAME: write_dxf(tmp_path / 's.dxf')})
    assert (store.get_job(run['job_id'])['folder'] / NAME).is_file()


def test_settings_validate_the_output_destination(tmp_path):
    assert Settings(data_dir=tmp_path, validate_roots=False).output_destination is None
    chosen = tmp_path / 'out'
    settings = Settings(data_dir=tmp_path, validate_roots=False, output_destination=str(chosen))
    assert settings.public_dict()['output_destination'] == str(chosen.resolve())
    with pytest.raises(ValueError, match='absolute'):
        Settings(data_dir=tmp_path, validate_roots=False, output_destination='relative/out')


def test_service_config_carries_the_destination_and_allows_clearing_it(tmp_path):
    service = ApplicationService(tmp_path / 'app', ROOT)
    assert service._config({})['output_destination'] is None
    service.update_settings({'output_destination': str(tmp_path / 'out')})
    assert service._config({})['output_destination'] == str((tmp_path / 'out').resolve())
    service.update_settings({'output_destination': None})
    assert service._config({})['output_destination'] is None


class SyntheticRunner(ScriptedRunner):
    async def preflight(self):
        return {'fixture': True}


def test_http_run_delivers_to_the_chosen_destination_and_tells_the_ai(tmp_path):
    root = sources(tmp_path)
    out = tmp_path / 'delivered'
    runner = SyntheticRunner({'26-000001': synthetic_part()})
    service = ApplicationService(tmp_path / 'app', ROOT, runner=runner)
    service.update_settings({'roots': [str(root)], 'stable_seconds': .001, 'scan_interval': .05,
                             'output_destination': str(out)})
    with TestClient(create_app(tmp_path / 'app', ROOT, service=service), base_url='http://127.0.0.1') as client:
        headers = {'X-Luan-Token': client.get('/api/health').json()['mutation_token']}
        assert client.post('/api/scan', json={}, headers=headers).status_code == 200
        job = client.get('/api/jobs').json()['jobs'][0]
        base = '/api/jobs/' + job['id']
        assert client.post(base + '/start', json={}, headers=headers).status_code == 200
        for _ in range(600):
            record = client.get(base).json()
            if record['status'] in {'completed', 'error'}:
                break
            time.sleep(.02)
        assert record['status'] == 'completed', record['run'].get('error')
    assert (out / 'job0_ALL.dxf').is_file()
    assert not (root / 'job0' / 'job0_ALL.dxf').exists()
    assert str(out.resolve()) in runner.requests[1].prompt  # the minimal prompt names the deliverable's place
