from pathlib import Path
import warnings
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', message='Using `httpx` with `starlette.testclient` is deprecated.*')
    from fastapi.testclient import TestClient
from LuanAppTools.service.api import create_app
ROOT = Path(__file__).resolve().parents[2]


def test_connection_partial_update_preserves_saved_endpoint(tmp_path):
    from LuanAppTools.service.controller import ApplicationService

    service = ApplicationService(tmp_path/'app', ROOT)
    service.update_connection({
        'active_provider':'custom',
        'gateway_url':'http://localhost:20128/v1',
        'gateway_model':'saved-model',
        'custom_auth_mode':'none',
    })
    with TestClient(create_app(tmp_path/'app', ROOT, False, service=service),
                    base_url='http://127.0.0.1') as client:
        headers = {'X-Luan-Token':client.get('/api/health').json()['mutation_token']}
        response = client.put('/api/connections', json={'active_provider':'claude'},
                              headers=headers)
        assert response.status_code == 200
        assert response.json()['active_provider'] == 'claude'
        assert response.json()['custom']['model'] == 'saved-model'


def test_workspace_root_can_be_selected_through_settings_api(tmp_path):
    app_dir = tmp_path/'app'
    selected = tmp_path/'shared-workspace'
    with TestClient(create_app(app_dir, ROOT, start_scheduler=False),
                    base_url='http://127.0.0.1') as client:
        headers = {'X-Luan-Token':client.get('/api/health').json()['mutation_token']}
        assert client.get('/api/settings').json()['workspace_root'] == str(app_dir.resolve())
        response = client.put('/api/settings', json={'workspace_root':str(selected)},
                              headers=headers)
        assert response.status_code == 200
        assert response.json()['workspace_root'] == str(selected.resolve())
        assert selected.is_dir()

def test_empty_installation_and_request_boundaries(tmp_path):
    with TestClient(create_app(tmp_path/'app', ROOT, start_scheduler=False), base_url='http://127.0.0.1') as client:
        response = client.get('/api/health')
        assert response.status_code == 200
        token = response.json()['mutation_token']
        assert client.get('/api/settings').json()['roots'] == []
        assert client.get('/api/jobs').json()['jobs'] == []
        assert client.post('/api/scan', json={}).status_code == 403
        headers = {'X-Luan-Token':token}
        assert client.post('/api/scan', json={}, headers=headers).status_code == 200
        assert client.post('/api/scan', content='{}', headers=headers).status_code == 415
        assert client.post('/api/scan', json={}, headers={**headers,'Origin':'http://evil.test'}).status_code == 403
        assert client.get('/api/jobs', headers={'Host':'evil.test'}).status_code == 403
        providers = client.get('/api/providers').json()
        assert providers['gateway']['status'] == 'not_selected'
        assert providers['gpt']['status'] == 'unavailable'

def test_files_pages_scoped_paths_and_reversible_revision_review(tmp_path):
    import asyncio
    from LuanAppTools.service.controller import ApplicationService
    from LuanAppTools.tests.test_controller import sources, until
    from LuanAppTools.tests.test_pipeline import ScriptedRunner,synthetic_part
    class Runner(ScriptedRunner):
        async def preflight(self): return {}
    service=ApplicationService(tmp_path/'app',ROOT,runner=Runner({'26-000001':synthetic_part()}))
    root=sources(tmp_path)
    service.update_settings({'roots':[str(root)],'stable_seconds':.001})
    async def prepare():
        await service.scan(); job=service.store.list_jobs()[0]
        await service.start(job['id']); await service.tick(); await until(lambda:not service.active)
        return service.store.get_job(job['id'])
    job=asyncio.run(prepare()); run_id=job['current_run']
    app=create_app(tmp_path/'app',ROOT,start_scheduler=False,service=service)
    with TestClient(app,base_url='http://127.0.0.1') as client:
        headers={'X-Luan-Token':client.get('/api/health').json()['mutation_token']}
        rows=client.get(f'/api/jobs/{job["id"]}/files').json()['files']
        source=next(f for f in rows if f['kind']=='source')
        assert source['page_count']==1
        assert client.get(source['download_url']).content.startswith(b'%PDF')
        page=client.get(source['pages_url'].replace('{page}','1'))
        assert page.status_code==200 and page.headers['content-type']=='image/png'
        assert client.get(f'/api/jobs/{job["id"]}/files/not-a-path').status_code==404
        preview=client.get(f'/api/jobs/{job["id"]}/preview').json()['previews'][0]
        assert '<svg' in client.get(preview['url']).text
        route=f'/api/jobs/{job["id"]}/review'
        assert client.post(route,json={'run_id':run_id,'reviewed':True},headers=headers).json()['reviewed']
        revoked=client.post(route,json={'run_id':run_id,'reviewed':False},headers=headers).json()
        assert not revoked['reviewed'] and len(revoked['reviews'])==2
        assert [r['reviewed'] for r in revoked['reviews']]==[True,False]
        assert client.post(route,json={'run_id':'obsolete'},headers=headers).status_code==409
        assert client.put('/api/settings',json={'gateway_url':'http://user:password@localhost/v1'},headers=headers).status_code==409
        assert client.put('/api/settings',json={'secret':'do-not-store'},headers=headers).status_code==422
        assert 'do-not-store' not in client.get('/api/settings').text


def test_offline_health_remains_actionable_and_folder_open_uses_host_operation(tmp_path):
    import asyncio
    from LuanAppTools.service.controller import ApplicationService
    from LuanAppTools.tests.test_controller import sources
    opened=[]
    service=ApplicationService(tmp_path/'app',ROOT,folder_opener=opened.append)
    root=sources(tmp_path)
    service.update_settings({'roots':[str(root)]})
    asyncio.run(service.scan()); job=service.store.list_jobs()[0]
    with TestClient(create_app(tmp_path/'app',ROOT,False,service=service),base_url='http://127.0.0.1') as client:
        headers={'X-Luan-Token':client.get('/api/health').json()['mutation_token']}
        response=client.post(f'/api/jobs/{job["id"]}/open-folder',json={'target':'source'},headers=headers)
        assert response.status_code==200 and opened==[root/'job0']
    root.rename(tmp_path/'disconnected')
    with TestClient(create_app(tmp_path/'app',ROOT,False),base_url='http://127.0.0.1') as client:
        assert client.get('/api/health').json()['roots']==[{'path':str(root),'available':False}]
        assert client.get('/api/settings').json()['roots']==[str(root)]
        assert len(client.get('/api/jobs').json()['jobs'])==1

def test_list_and_action_projections_omit_checkpoint_and_never_hash_sources(tmp_path,monkeypatch):
    import asyncio
    from LuanAppTools.service.controller import ApplicationService
    from LuanAppTools.tests.test_controller import sources
    service=ApplicationService(tmp_path/'app',ROOT)
    root=sources(tmp_path)
    service.update_settings({'roots':[str(root)],'stable_seconds':.001})
    asyncio.run(service.scan()); job=service.store.list_jobs()[0]
    run=asyncio.run(service.start(job['id']))
    service.store.save_checkpoint(run['id'],{'private_tool_context':'SENSITIVE_CONTEXT_'+('x'*1000000)})
    service.store.append_event(run['id'],'provider_activity',{'model':'haiku-5.5','prompt':'SENSITIVE_PROMPT','tool_result':'x'*1000000})
    app=create_app(tmp_path/'app',ROOT,False,service=service)
    with TestClient(app,base_url='http://127.0.0.1') as client:
        def forbidden(*args,**kwargs): raise AssertionError('List poll must not hash files')
        monkeypatch.setattr('LuanAppTools.service.controller.file_hash',forbidden)
        response=client.get('/api/jobs')
        assert response.status_code==200 and len(response.content)<10000
        assert 'checkpoint' not in response.text and 'SENSITIVE_CONTEXT' not in response.text
        headers={'X-Luan-Token':client.get('/api/health').json()['mutation_token']}
        paused=client.post(f'/api/jobs/{job["id"]}/pause',json={},headers=headers)
        assert paused.status_code==200 and 'checkpoint' not in paused.text
        events=client.get(f'/api/jobs/{job["id"]}/events').json()['events']
        assert events[0]['payload']=={'model':'haiku-5.5'}

def test_cli_starts_real_loopback_http_without_ai(tmp_path):
    import httpx
    import socket
    import subprocess
    import sys
    import time
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    process=subprocess.Popen([sys.executable,'-m','LuanAppTools','--data-dir',str(tmp_path/'app'),'--repo-root',str(ROOT),'--port',str(port)],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False) as client:
            for _ in range(200):
                try:
                    response=client.get('/api/health')
                    if response.status_code==200: break
                except httpx.TransportError: pass
                if process.poll() is not None: raise AssertionError(process.stderr.read().decode())
                time.sleep(.02)
            else: raise AssertionError('HTTP listener did not start')
            assert response.json()['status']=='ok'
            token=response.json()['mutation_token']
            assert client.post('/api/scan',json={},headers={'X-Luan-Token':token}).status_code==200
            assert client.get('/api/jobs').json()=={'jobs':[]}
            assert client.get('/api/health',headers={'Host':'192.168.1.8'}).status_code==403
    finally:
        process.terminate()
        process.communicate(timeout=10)


def test_slow_file_listing_keeps_health_responsive(tmp_path, monkeypatch):
    import asyncio
    import threading
    import httpx
    from LuanAppTools.service.controller import ApplicationService
    service = ApplicationService(tmp_path/'app', ROOT)
    entered = threading.Event()
    release = threading.Event()
    def slow_files(job_id):
        entered.set()
        release.wait(2)
        return []
    monkeypatch.setattr(service, 'files', slow_files)
    app = create_app(tmp_path/'app', ROOT, start_scheduler=False, service=service)
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://127.0.0.1') as client:
            request = asyncio.create_task(client.get('/api/jobs/job1/files'))
            try:
                assert await asyncio.to_thread(entered.wait, 3)
                # If file I/O blocks the event loop, its timeout has already
                # elapsed and the listing is done before health can run.
                response = await client.get('/api/health')
                assert response.status_code == 200
                assert not request.done()
            finally:
                release.set()
                await request
    asyncio.run(scenario())
