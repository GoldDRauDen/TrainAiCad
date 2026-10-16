"""HTTP → scheduler → actual canonical/export/readback → local publication.

ScriptedRunner substitutes external AI only. Source geometry is synthetic.
"""
import time
from pathlib import Path
import ezdxf
from fastapi.testclient import TestClient
from LuanAppTools.service.api import create_app
from LuanAppTools.service.controller import ApplicationService
from LuanAppTools.tests.test_controller import sources
from LuanAppTools.tests.test_pipeline import ScriptedRunner, synthetic_part

ROOT = Path(__file__).resolve().parents[2]

class SyntheticRunner(ScriptedRunner):
    async def preflight(self):
        return {'fixture': True}


def test_http_mixed_output_review_history_and_rescan(tmp_path):
    root = sources(tmp_path)
    service = ApplicationService(tmp_path/'app', ROOT, runner=SyntheticRunner({
        '26-000001': synthetic_part(),
        '26-000002': synthetic_part('26-000002', review=True),
    }))
    service.update_settings({'roots':[str(root)], 'stable_seconds':.001, 'scan_interval':.05})
    with TestClient(create_app(tmp_path/'app', ROOT, service=service), base_url='http://127.0.0.1') as client:
        headers = {'X-Luan-Token':client.get('/api/health').json()['mutation_token']}
        assert client.post('/api/scan', json={}, headers=headers).status_code == 200
        job = client.get('/api/jobs').json()['jobs'][0]
        base = '/api/jobs/'+job['id']
        first = client.post(base+'/start', json={'individual':True}, headers=headers).json()['run']
        def completed():
            for _ in range(600):
                record = client.get(base).json()
                if record['status'] in {'completed','error'}:
                    assert record['status']=='completed', record['run'].get('error')
                    return record
                time.sleep(.02)
            raise AssertionError('Synthetic job did not finish')
        record = completed()
        assert record['technical_counts']=={'PASS':1,'REVIEW':1}
        assert not record['reviewed']
        outputs = [f for f in record['files'] if f['kind']=='output' and f['current']]
        assert {f['name'] for f in outputs}=={'job0_ALL_REVIEW_ONLY.dxf','26-000001.dxf'}
        for f in outputs:
            assert client.get(f['download_url']).status_code==200
            assert len(ezdxf.readfile(f['path']).modelspace())>0
        assert client.post(base+'/review',json={'run_id':first['id']},headers=headers).json()['reviewed']
        assert client.post('/api/scan',json={},headers=headers).status_code==200
        assert client.get(base).json()['run']['id']==first['id']
        assert client.post(base+'/start',json={'force':True,'individual':True},headers=headers).status_code==200
        second = completed()
        assert second['run']['id']!=first['id'] and len(second['runs'])==2
        assert not second['reviewed']
        history = [f for f in second['files'] if f['kind']=='output' and f['run_id']==first['id']]
        assert len(history)==2 and all(f['download_url'] and f['stale'] for f in history)
        for f in history:
            assert client.get(f['download_url']).status_code==200
        assert client.post(base+'/review',json={'run_id':first['id']},headers=headers).status_code==409
        assert (root/'job0'/'job0_ALL_REVIEW_ONLY.dxf').exists()
        assert not (root/'job0'/'parts_dxf'/'26-000002.dxf').exists()
