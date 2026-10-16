"""Service acceptance: actual SQLite, source files and shared admission."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import fitz
import pytest
from LuanAppTools.service.controller import ApplicationService

ROOT = Path(__file__).resolve().parents[2]

def sources(tmp_path, count=1):
    root = tmp_path / 'sources'; root.mkdir()
    for i in range(count):
        folder = root / f'job{i}'; folder.mkdir()
        with fitz.open() as doc:
            doc.new_page().insert_text((30,30), f'SYNTHETIC {i}')
            doc.save(folder / 'source.pdf')
    return root

async def until(predicate):
    for _ in range(2000):
        if predicate(): return
        await asyncio.sleep(.01)
    raise AssertionError('Service did not reach expected state')

def test_shared_admission_survives_settings_change(tmp_path):
    async def scenario():
        service = ApplicationService(tmp_path/'app', ROOT)
        service.update_settings({'max_ai_calls': 2})
        entered = 0; peak = 0; gate = asyncio.Event()
        async def work(model):
            nonlocal entered, peak
            async with service.model_slot(model):
                entered += 1; peak = max(peak, entered)
                await gate.wait(); entered -= 1
        tasks = [asyncio.create_task(work('opus-5.5')) for _ in range(2)]
        await until(lambda: entered == 1)
        tasks += [asyncio.create_task(work('sonnet-5.5')) for _ in range(3)]
        await until(lambda: entered == 2)
        service.update_settings({'max_ai_calls': 1})
        await asyncio.sleep(.03)
        assert entered == 2
        gate.set(); await asyncio.gather(*tasks)
        assert peak == 2
    asyncio.run(scenario())

def test_discovery_pause_generation_and_single_lifecycle(tmp_path):
    async def scenario():
        root = sources(tmp_path)
        service = ApplicationService(tmp_path/'app', ROOT)
        service.update_settings({'roots':[str(root)], 'stable_seconds':.001})
        await service.scan()
        job = service.store.list_jobs()[0]
        assert not job['tracked'] and not job['current_run']
        run = await service.start(job['id'])
        await service.pause(job['id'])
        with fitz.open() as doc:
            doc.new_page().insert_text((30,30), 'SYNTHETIC CHANGED')
            doc.save(root/'job0'/'source.pdf')
        await service.refresh_sources()
        latest = service.store.get_run(service.store.get_job(job['id'])['current_run'])
        assert latest['id'] != run['id']
        assert latest['status'] == 'paused'
        assert service.store.get_run(run['id'])['status'] == 'superseded'
        assert not service.store.may_publish(run['id'])
        await service.refresh_sources()
        assert service.store.get_job(job['id'])['generation']==2
        await service.open(start_scheduler=False)
        other = ApplicationService(tmp_path/'app', ROOT)
        with pytest.raises(RuntimeError, match='already'):
            await other.open(start_scheduler=False)
        await service.close()
        await other.open(start_scheduler=False); await other.close()
    asyncio.run(scenario())

def test_offline_saved_root_does_not_block_setup(tmp_path):
    root=sources(tmp_path)
    service=ApplicationService(tmp_path/'app',ROOT)
    service.update_settings({'roots':[str(root)]})
    root.rename(tmp_path/'offline')
    reopened=ApplicationService(tmp_path/'app',ROOT)
    assert reopened.settings.public_dict()['roots']==[str(root)]
    assert reopened.store.list_jobs()==[]


def test_real_provider_seam_pause_ack_resume_and_current_output(tmp_path):
    from LuanAppTools.tests.test_pipeline import ScriptedRunner, synthetic_part
    class Runner(ScriptedRunner):
        async def preflight(self): return {'version':'synthetic-test-only','auth_method':'test'}
        async def complete(self,request,**kwargs):
            if '\"stage\": \"solve\"' in request.prompt:
                await service.pause(job['id'])
                assert service.store.get_run(run['id'])['status']=='pause_requested'
            return await super().complete(request,**kwargs)
    async def scenario():
        nonlocal service,job,run
        root=sources(tmp_path)
        runner=Runner({'26-000001':synthetic_part()})
        service=ApplicationService(tmp_path/'app',ROOT,runner=runner)
        service.update_settings({'roots':[str(root)],'stable_seconds':.001})
        await service.scan(); job=service.store.list_jobs()[0]
        run=await service.start(job['id'],difficulty='medium',individual=True)
        await service.tick(); await until(lambda:not service.active)
        assert service.store.get_run(run['id'])['status']=='paused'
        assert service.store.attempts(run['id'],'26-000001')==1
        assert service.store.get_run(run['id'])['checkpoint']['parts']['26-000001']['phase']=='qa_ready'
        service.update_settings({'models':{**service.settings.models,'medium':{'model':'opus-5.5','effort':'max'}}})
        await service.resume(job['id']); await service.tick(); await until(lambda:not service.active)
        assert service.store.get_run(run['id'])['status']=='completed'
        assert service.store.attempts(run['id'],'26-000001')==1
        solve=[r for r in runner.requests if '\"stage\": \"solve\"' in r.prompt]
        assert len(solve)==1 and solve[0].model=='sonnet-5.5'
        detail=service.job(job['id'])
        assert detail['technical_counts']=={'PASS':1} and detail['usage']=={}
        assert len([f for f in detail['files'] if f['kind']=='output' and f['current']])==2
        assert not detail['reviewed']
        assert (await service.review(job['id'],run_id=run['id']))['reviewed']
        output=next(f for f in detail['files'] if f['kind']=='output')
        Path(output['path']).write_text('customer-changed')
        assert not service.job(job['id'])['reviewed']
        assert next(f for f in service.files(job['id']) if f['id']==output['id'])['download_url'] is None
    service=job=run=None
    asyncio.run(scenario())

def test_max_three_jobs_waiting_releases_slots_and_cancel_stops(tmp_path):
    from LuanAppTools.ai.protocol import ProviderError
    class BlockingRunner:
        def __init__(self): self.calls=0; self.peak=0; self.active=0
        async def preflight(self): return {}
        async def complete(self,request,*,cancel,**kwargs):
            self.calls+=1; self.active+=1; self.peak=max(self.peak,self.active)
            try:
                await cancel.wait()
                raise asyncio.CancelledError()
            finally: self.active-=1
    async def scenario():
        root=sources(tmp_path,4); runner=BlockingRunner()
        service=ApplicationService(tmp_path/'app',ROOT,runner=runner)
        service.update_settings({'roots':[str(root)],'stable_seconds':.001})
        await service.scan(); jobs=service.store.list_jobs()
        for job in jobs: await service.start(job['id'])
        await service.tick(); assert len(service.active)==3
        await until(lambda:runner.active==2)
        assert runner.peak==2
        for job in jobs[:3]: await service.cancel(job['id'])
        await until(lambda:not service.active)
        await service.tick(); assert len(service.active)==1
        await service.close(); assert not service.active and runner.active==0
    asyncio.run(scenario())


def test_rejected_usage_delays_without_reset_and_unknown_restart_blocks(tmp_path):
    from LuanAppTools.ai.protocol import ProviderError
    class Reject:
        def __init__(self,outcome): self.outcome=outcome; self.calls=0
        async def preflight(self): return {}
        async def complete(self,*args,**kwargs):
            self.calls+=1
            raise ProviderError('rate_limit' if self.outcome=='rejected' else 'connection_error','synthetic transport',outcome=self.outcome)
    async def scenario():
        root=sources(tmp_path); runner=Reject('rejected')
        service=ApplicationService(tmp_path/'app',ROOT,runner=runner)
        service.update_settings({'roots':[str(root)],'stable_seconds':.001,'retry_seconds':.1})
        await service.scan(); job=service.store.list_jobs()[0]; run=await service.start(job['id'])
        await service.tick(); await until(lambda:not service.active)
        assert service.store.get_run(run['id'])['status']=='waiting_usage'
        assert not service.store.get_run(run['id'])['lease']
        await service.tick(); assert runner.calls==1
        await asyncio.sleep(.12); runner.outcome='unknown'
        await service.tick(); await until(lambda:not service.active)
        current=service.store.get_run(run['id'])
        assert current['status']=='reconciliation_required' and current['checkpoint']['pending']
        reopened=ApplicationService(tmp_path/'app',ROOT,runner=runner)
        await reopened.open(start_scheduler=False)
        await reopened.tick(); assert runner.calls==2
        with pytest.raises(ValueError,match='Interrupted request'):
            await reopened.resume(job['id'])
        await reopened.close()
    asyncio.run(scenario())


def test_restart_process_verification_precedes_lease_release(tmp_path):
    async def scenario():
        root=sources(tmp_path); calls=[]
        async def stop(identity):
            calls.append(identity['token'])
            assert service.store.get_run(run['id'])['lease']==lease
            from LuanAppTools.ai.protocol import ProviderError
            raise ProviderError('reconciliation_required','synthetic identity mismatch')
        service=ApplicationService(tmp_path/'app',ROOT,process_stopper=stop)
        service.update_settings({'roots':[str(root)],'stable_seconds':.001})
        await service.scan(); job=service.store.list_jobs()[0]; run=await service.start(job['id'])
        lease=service.store.claim_run(run['id'],'crashed')
        service.store.append_event(run['id'],'provider_process_started',{'process':{'token':'test-only-unverified'}})
        await service.open(start_scheduler=False)
        assert calls==['test-only-unverified']
        assert service.store.get_run(run['id'])['lease']==lease
        # Even a superseding generation may not overlap the unverified process.
        newer=service.store.create_run(job['id'],'new-source',run['repo_commit'],config=run['config'])
        await service.tick(); assert not service.active
        await service.close()
        async def verified(identity): return True
        resumed=ApplicationService(tmp_path/'app',ROOT,process_stopper=verified)
        await resumed.open(start_scheduler=False)
        assert any(e['kind']=='provider_process_exited' for e in resumed.store.events_since(run['id']))
        await resumed.close()
    asyncio.run(scenario())


def test_gateway_explicit_actual_model_scoped_probe(tmp_path):
    from LuanAppTools.ai.gateway import GatewayCapabilityReport
    from LuanAppTools.tests.test_pipeline import ScriptedRunner,synthetic_part
    class Runner(ScriptedRunner):
        async def preflight(self): return {}
    class Gateway(Runner):
        def __init__(self,endpoint): super().__init__({'26-000001':synthetic_part()}); self.endpoint=endpoint
        async def probe(self,**kwargs):
            probes.append((self.endpoint,kwargs['model'],kwargs['effort'],kwargs['authorized']))
            return GatewayCapabilityReport(self.endpoint,kwargs['model'],kwargs['effort'],0,'verified','verified','verified',kwargs['model'],kwargs['effort'])
    async def scenario():
        root=sources(tmp_path); primary=Runner({'26-000001':synthetic_part()})
        gateways=[]
        def factory(endpoint):
            gateway=Gateway(endpoint); gateways.append(gateway); return gateway
        service=ApplicationService(tmp_path/'app',ROOT,runner=primary,gateway_factory=factory)
        service.update_settings({'roots':[str(root)],'stable_seconds':.001,'gateway_model':'free-actual-model'})
        await service.scan(); job=service.store.list_jobs()[0]; run=await service.start(job['id'])
        assert not probes and not gateways
        await service.use_gateway(job['id'])
        assert probes==[('http://localhost:20128/v1','free-actual-model','high',True)]
        await service.tick(); await until(lambda:not service.active)
        assert service.store.get_run(run['id'])['status']=='completed'
        assert not primary.requests
        assert len(gateways[-1].requests)==3
        assert all(r.model=='free-actual-model' and r.gateway_authorized for r in gateways[-1].requests)
        assert service.job(job['id'])['provider']=='9router'
        assert (await service.providers())['gateway']['status']=='verified'
        service.update_settings({'gateway_model':'other-model'})
        assert (await service.providers())['gateway']['status']=='not_selected'
    probes=[]
    asyncio.run(scenario())


@pytest.mark.parametrize('action',['cancel','restart','timeout','pause','source_change'])
def test_owned_publication_blocked_child_stops_before_control_write_and_retries(tmp_path,action):
    """A real child blocks inside the real Publisher's SQLite publication guard."""
    import sys
    import time
    import ezdxf
    from LuanAppTools.service.publication import PublicationError
    marker=tmp_path/'child-copy-entered'
    program=("import time\nfrom pathlib import Path\n"
             "from LuanAppTools.core.publisher import Publisher\n"
             "from LuanAppTools.service.publication import worker\n"
             "def block(*args):\n"
             f"    Path({str(marker)!r}).write_text('inside actual publication guard')\n"
             "    time.sleep(60)\n"
             "Publisher._copy_verified=staticmethod(block)\nworker()\n")
    async def scenario():
        root=sources(tmp_path)
        service=ApplicationService(tmp_path/'app',ROOT,publication_command=[sys.executable,'-c',program])
        service.update_settings({'roots':[str(root)],'stable_seconds':.001,'output_timeout':2.0 if action=='timeout' else 30.0})
        await service.scan(); job=service.store.list_jobs()[0]; run=await service.start(job['id'])
        stage=tmp_path/'stage.dxf'; doc=ezdxf.new(); doc.modelspace().add_circle((0,0),5); doc.saveas(stage)
        service.store.save_checkpoint(run['id'],{'export':{'files':{'job0_ALL.dxf':str(stage)}}})
        await service.tick(); await until(marker.exists)
        assert service.store.get_run(run['id'])['publication']
        events=service.store.events_since(run['id']); identity=next(e['payload']['process'] for e in events if e['kind']=='publication_process_started')
        if action=='cancel':
            before=time.monotonic(); await service.cancel(job['id'])
            assert time.monotonic()-before < 5
            await until(lambda:not service.active)
            assert service.store.get_run(run['id'])['status']=='cancelled'
        elif action=='pause':
            await service.pause(job['id'])
            await until(lambda:not service.active)
            assert service.store.get_run(run['id'])['status']=='paused'
            service.publisher.command=(sys.executable,'-m','LuanAppTools.service.publication','--worker')
            await service.resume(job['id']); await service.tick(); await until(lambda:not service.active)
            assert service.store.get_run(run['id'])['status']=='completed'
        elif action=='source_change':
            with fitz.open() as doc:
                doc.new_page().insert_text((30,30),'LATEST SYNTHETIC SOURCE')
                doc.save(root/'job0'/'source.pdf')
            await service.refresh_sources()
            await until(lambda:not service.active)
            assert service.store.get_run(run['id'])['status']=='superseded'
            latest=service.store.get_run(service.store.get_job(job['id'])['current_run'])
            assert latest['id']!=run['id'] and latest['status']=='queued'
            assert not latest['config']['gateway_authorized']
        elif action=='timeout':
            await until(lambda:not service.active)
            assert service.store.get_run(run['id'])['status']=='waiting_output'
            service.publisher.command=(sys.executable,'-m','LuanAppTools.service.publication','--worker')
            await service.resume(job['id']); await service.tick(); await until(lambda:not service.active)
            assert service.store.get_run(run['id'])['status']=='completed'
        else:
            before=time.monotonic()
            recovered=ApplicationService(tmp_path/'app',ROOT)
            assert time.monotonic()-before < 2  # Constructor never waits on orphan's write lock.
            await recovered.open(start_scheduler=False)
            await until(lambda:not service.active)
            recovered_run=recovered.store.get_run(run['id'])
            assert recovered_run['status']=='waiting_output' and not recovered_run['lease']
            await recovered.resume(job['id']); await recovered.tick(); await until(lambda:not recovered.active)
            assert recovered.store.get_run(run['id'])['status']=='completed'
            await recovered.close()
        final_events=service.store.events_since(run['id'])
        assert any(e['kind']=='publication_process_exited' and e['payload']['process']['token']==identity['token'] for e in final_events)
        if action not in {'cancel','source_change'}:
            assert (root/'job0'/'job0_ALL.dxf').is_file()
        else:
            assert not (root/'job0'/'job0_ALL.dxf').exists()
        assert service.store.attempts(run['id'],'26-000001')==0
    asyncio.run(scenario())


def test_contended_parent_writes_keep_loop_and_publisher_deadlines_responsive(tmp_path):
    import sys
    import time
    import ezdxf
    from LuanAppTools.tests.test_pipeline import ScriptedRunner,synthetic_part
    marker=tmp_path/'inside-child-guard'
    program=("import time\nfrom pathlib import Path\n"
             "from LuanAppTools.core.publisher import Publisher\n"
             "from LuanAppTools.service.publication import worker\n"
             "original=Publisher._copy_verified\n"
             f"def delay(*args):\n Path({str(marker)!r}).write_text('held')\n time.sleep(3)\n return original(*args)\n"
             "Publisher._copy_verified=staticmethod(delay)\nworker()\n")
    async def scenario():
        release=asyncio.Event(); provider_progress=asyncio.Event(); provider_entered=asyncio.Event()
        class Runner(ScriptedRunner):
            async def preflight(self): return {}
            async def complete(self,request,*,emit,**kwargs):
                provider_entered.set()
                await release.wait()
                await emit({'kind':'usage','session_id':'contention-fixture','event_key':'measured-once','metrics':{'input_tokens':1}})
                provider_progress.set()
                return await super().complete(request,emit=emit,**kwargs)
        root=sources(tmp_path,3)
        service=ApplicationService(tmp_path/'app',ROOT,runner=Runner({'26-000001':synthetic_part()}),publication_command=[sys.executable,'-c',program])
        service.update_settings({'roots':[str(root)],'stable_seconds':.001,'output_timeout':2.0})
        await service.scan(); jobs=service.store.list_jobs()
        runs=[await service.start(job['id']) for job in jobs]
        stage=tmp_path/'stage.dxf'; doc=ezdxf.new(); doc.modelspace().add_circle((0,0),5); doc.saveas(stage)
        for i in (0,2):
            service.store.save_checkpoint(runs[i]['id'],{'export':{'files':{f'job{i}_ALL.dxf':str(stage)}}})
        await service.tick(); await until(marker.exists)
        await asyncio.wait_for(provider_entered.wait(),6)
        scan=asyncio.create_task(service.scan())
        pause=asyncio.create_task(service.pause(jobs[1]['id']))
        release.set(); before=time.monotonic()
        await asyncio.sleep(.1)
        assert time.monotonic()-before < .6, 'SQLite contention stalled the event loop/deadline timers'
        try:
            await asyncio.wait_for(asyncio.gather(scan,pause),6)
            await asyncio.wait_for(provider_progress.wait(),6)
            await until(lambda:not service.active)
            assert service.store.get_run(runs[0]['id'])['status']=='waiting_output'
            assert service.store.get_run(runs[2]['id'])['status']=='waiting_output'
            assert not (root/'job0'/'job0_ALL.dxf').exists()
            assert not (root/'job2'/'job2_ALL.dxf').exists()
            assert service.store.get_job(jobs[1]['id'])['paused']
        finally:
            await service.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('action',['pause','cancel','source_change'])
def test_gateway_probe_rechecks_later_control_actions(tmp_path,action):
    from LuanAppTools.ai.gateway import GatewayCapabilityReport
    async def scenario():
        entered=asyncio.Event(); release=asyncio.Event()
        class Gateway:
            def __init__(self,endpoint): self.endpoint=endpoint
            async def probe(self,**kwargs):
                entered.set(); await release.wait()
                return GatewayCapabilityReport(self.endpoint,kwargs['model'],kwargs['effort'],0,'verified','verified','verified',kwargs['model'],kwargs['effort'])
        root=sources(tmp_path)
        service=ApplicationService(tmp_path/'app',ROOT,gateway_factory=Gateway)
        service.update_settings({'roots':[str(root)],'stable_seconds':.001,'gateway_model':'synthetic-exact-model'})
        await service.scan(); job=service.store.list_jobs()[0]; run=await service.start(job['id'])
        probe=asyncio.create_task(service.use_gateway(job['id'])); await entered.wait()
        if action=='pause':
            response=await service.pause(job['id']); assert response['status']=='paused'
        elif action=='cancel':
            await service.cancel(job['id'])
        else:
            # Simulate an independently committed source generation while the probe awaits.
            service.store.create_run(job['id'],'new-stable-source',run['repo_commit'],config=run['config'])
        release.set()
        if action=='pause':
            result=await probe
            assert result['status']=='paused'
            assert service.store.get_job(job['id'])['paused']
            assert result['config']['gateway_authorized']
            await service.tick(); assert not service.active
        else:
            with pytest.raises((ValueError,asyncio.CancelledError)):
                await probe
            assert not service.store.get_run(run['id'])['config']['gateway_authorized']
        await service.close()
    asyncio.run(scenario())


def test_resume_never_exposes_queued_with_durable_pause(tmp_path):
    async def scenario():
        service=ApplicationService(tmp_path/'app',ROOT)
        root=sources(tmp_path)
        service.update_settings({'roots':[str(root)],'stable_seconds':.001})
        await service.scan(); job=service.store.list_jobs()[0]
        run=await service.start(job['id']); await service.pause(job['id'])
        original=service.mutations.run
        async def observe(operation,*args,**kwargs):
            result=await original(operation,*args,**kwargs)
            state=service.store.get_run(run['id'])
            assert not (state['status']=='queued' and service.store.get_job(job['id'])['paused'])
            return result
        service.mutations.run=observe
        resumed=await service.resume(job['id'])
        assert resumed['status']=='queued' and not service.store.get_job(job['id'])['paused']
        await service.close()
    asyncio.run(scenario())


def test_worker_failure_release_cannot_overwrite_later_cancel(tmp_path):
    from types import SimpleNamespace
    async def scenario():
        service=ApplicationService(tmp_path/'app',ROOT)
        root=sources(tmp_path)
        service.update_settings({'roots':[str(root)],'stable_seconds':.001})
        await service.scan(); job=service.store.list_jobs()[0]
        run=await service.start(job['id'])
        lease=service.store.claim_run(run['id'],'test')
        original=service.mutations.run
        async def interleave(operation,*args,**kwargs):
            result=await original(operation,*args,**kwargs)
            if operation==service.store.release_run:
                await original(service.store.set_run_status,run['id'],'cancelled')
            return result
        service.mutations.run=interleave
        await service._release_if_current(run,SimpleNamespace(lease=lease),'waiting_output','copy stopped')
        assert service.store.get_run(run['id'])['status']=='cancelled'
        await service.close()
    asyncio.run(scenario())
