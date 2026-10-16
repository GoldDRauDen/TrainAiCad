"""One durable scheduler; provider/CAD/publication gates remain in their owners."""
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

from LuanAppTools.ai.claude import ClaudeRunner, stop_owned_process
from LuanAppTools.ai.gateway import GatewayRunner
from LuanAppTools.ai.protocol import ProviderError
from LuanAppTools.cad.pipeline import CadPipeline, PipelineError, Paused, RunControl, reconcile_request
from LuanAppTools.cad.repository import PinnedRepository
from LuanAppTools.core.settings import Settings
from LuanAppTools.core.sources import discover_jobs, snapshot_job, contained_path, file_hash
from LuanAppTools.core.store import Store
from .publication import OwnedPublisher, PublicationError
from .mutations import AsyncMutations


class ApplicationService:
    def __init__(self, data_dir: Path, repo_root: Path, *, runner=None,
                 gateway_factory=GatewayRunner, pipeline_factory=CadPipeline,
                 process_stopper=stop_owned_process, folder_opener=None, publication_command=None):
        self.data_dir = Path(data_dir).resolve()
        self.repo_root = Path(repo_root).resolve()
        self.settings = Settings.load(self.data_dir, validate_roots=False)
        self.store = Store(self.data_dir / 'state.sqlite',busy_timeout=25)
        self.mutations = AsyncMutations()
        self.publisher = OwnedPublisher(self.store,self.data_dir/'history',self.repo_root,command=publication_command,mutation=self.mutations.run)
        self.runner = runner or ClaudeRunner()
        self.gateway_factory = gateway_factory
        self.pipeline_factory = pipeline_factory
        self.process_stopper = process_stopper
        self.folder_opener = folder_opener or self._open_folder
        self.owner = uuid.uuid4().hex
        self.active = {}
        self.controls = {}
        self._ai_active = self._opus_active = 0
        self._scheduler = None
        self._lock_file = None
        self._closing = False
        self._job_locks = {}
        self._repo_locks = {}
        self._probes = {}
        self._retry_at = {}
        self._provider = {'status':'unchecked', 'message':'Checked when requested or before work starts'}
        self.gateway_reports = {}
        self._blocked_jobs = set()
        self.last_error = None

    async def open(self, *, start_scheduler=True):
        if self._lock_file:
            raise RuntimeError('Service already open')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        stream = (self.data_dir / 'service.lock').open('a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                stream.seek(0); stream.write(b'0'); stream.flush(); stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            stream.close()
            raise RuntimeError('Another LuanAppTools service is already active for this data directory') from exc
        self._lock_file = stream
        self._closing = False
        if self.mutations._closing:
            self.mutations=AsyncMutations()
            self.publisher.mutation=self.mutations.run
        try:
            await self.recover()
            if start_scheduler:
                self._scheduler = asyncio.create_task(self._loop())
        except BaseException:
            self._unlock(); raise
        return self

    def _unlock(self):
        if self._lock_file:
            if os.name == 'nt':
                import msvcrt
                self._lock_file.seek(0); msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
            self._lock_file.close(); self._lock_file = None

    async def close(self):
        self._closing = True
        if self._scheduler:
            self._scheduler.cancel()
            await asyncio.gather(self._scheduler, return_exceptions=True)
            self._scheduler = None
        for cancel,task in list(self._probes.values()):
            cancel.set(); task.cancel()
        if self._probes:
            await asyncio.gather(*(task for _,task in list(self._probes.values())),return_exceptions=True)
        self.publisher.signal_all()
        for control in self.controls.values():
            control.cancel.set()
        for run_id in list(self.publisher.children):
            await self.publisher.stop(run_id)
        tasks = list(self.active.values())
        if tasks:
            _, pending = await asyncio.wait(tasks, timeout=self.settings.shutdown_seconds)
            for task in pending:
                task.cancel()
            # Owned providers reap their children in finally before returning.
            await asyncio.gather(*tasks, return_exceptions=True)
        await self.mutations.close()
        self._unlock()

    async def recover(self):
        for run in self.store.list_runs():
            events = self.store.events_since(run['id'], limit=1000000)
            exited = {e['payload']['process']['token'] for e in events if e['kind'] in {'provider_process_exited','publication_process_exited'}}
            unconfirmed = [e for e in events if e['kind'] in {'provider_process_started','publication_process_started'} and e['payload']['process']['token'] not in exited]
            stopped = True
            for event in unconfirmed:
                identity=event['payload']['process']
                try:
                    await self.process_stopper(identity)  # False positively means it already exited.
                    kind=event['kind'].replace('_started','_exited')
                    await self.mutations.run(self.store.append_event,run['id'],kind,{'kind':kind,'process':identity,'recovered':True})
                except (ProviderError,OSError,ValueError):
                    stopped = False
            if not stopped:
                self._blocked_jobs.add(run['job_id'])
                await self.mutations.run(self.store.append_event,run['id'], 'recovery_blocked', {'message':'Process identity cannot be verified; lease retained'})
                if run['status'] not in {'completed','cancelled','error','superseded'}:
                    await self.mutations.run(self.store.set_run_status,run['id'], 'reconciliation_required', error='Unverified previous process; lease retained')
                continue
            # A still-draining owner may have released its lease while the
            # recovered child was being reaped. Never use the stale snapshot.
            run = self.store.get_run(run['id'])
            if not run['lease'] or run['status'] in {'completed','cancelled','error','superseded'}:
                continue
            status = 'reconciliation_required' if run['checkpoint'].get('pending') else ('paused' if self.store.get_job(run['job_id'])['paused'] else 'queued')
            if run['publication']:
                status = 'paused' if self.store.get_job(run['job_id'])['paused'] else 'waiting_output'
            released = await self.mutations.run(self.store.release_run,run['id'], run['lease'], status=status,if_current=True)
            if released:
                await self.mutations.run(self.store.append_event,run['id'],'recovered',{'status':status})

    def update_settings(self, changes: dict):
        if not isinstance(changes, dict):
            raise ValueError('Expected a JSON object')
        if any(value is None and key != 'individual_destination' for key,value in changes.items()):
            raise ValueError('Only individual_destination may be null')
        allowed = set(self.settings.public_dict())
        if set(changes) - allowed:
            raise ValueError('Unknown settings: ' + ', '.join(sorted(set(changes)-allowed)))
        settings = Settings(self.data_dir, **{**self.settings.public_dict(), **changes})
        settings.save(); self.settings = settings
        return settings.public_dict()

    @asynccontextmanager
    async def model_slot(self, model, *, cancel=None):
        opus = 'opus' in model.lower()
        while self._ai_active >= self.settings.max_ai_calls or (opus and self._opus_active >= 1):
            if cancel is not None and cancel.is_set():
                raise asyncio.CancelledError()
            await asyncio.sleep(.02)
        # No await between checking and acquiring: shared across live settings changes.
        self._ai_active += 1; self._opus_active += int(opus)
        try:
            yield
        finally:
            self._ai_active -= 1; self._opus_active -= int(opus)

    def _allowed_job(self, job_id):
        job = self.store.get_job(job_id)
        for root in self.settings.roots:
            if job['folder'].is_relative_to(root):
                if job['folder'] == root:
                    # Validate root ancestry as well.
                    contained_path(root, 'source-scope-check')
                else:
                    contained_path(root, job['folder'].relative_to(root))
                return job
        raise ValueError('Job is outside configured source roots')

    def _owned(self, job_id=None):
        return [o['path'] for o in self.store.outputs(job_id=job_id, current_only=False)]

    async def scan(self):
        found = await asyncio.to_thread(discover_jobs, self.settings.roots, owned_paths=self._owned())
        for source in found:
            await self.mutations.run(self.store.register_job,source.folder)
        return {'discovered':len(found), 'jobs':self.jobs()}

    def _config(self, options):
        allowed = {'difficulty','individual','parts_destination','force'}
        if set(options)-allowed:
            raise ValueError('Unknown start option')
        difficulty = options.get('difficulty', self.settings.default_difficulty)
        individual = options.get('individual', self.settings.individual_output)
        destination = options.get('parts_destination', self.settings.individual_destination)
        if difficulty not in {'auto','easy','medium','hard'} or type(individual) is not bool or type(options.get('force',False)) is not bool:
            raise ValueError('Invalid start options')
        if destination is not None:
            destination = Path(destination).expanduser().resolve(strict=True)
            approved = self.settings.individual_destination
            if not approved or not destination.is_relative_to(Path(approved)) or not destination.is_dir():
                raise ValueError('Individual destination must be within the configured individual destination')
            if destination != Path(approved):
                contained_path(Path(approved), destination.relative_to(approved))
            else:
                contained_path(destination, 'destination-scope-check')
        return {'difficulty':difficulty, 'individual':individual, 'parts_destination':str(destination) if destination else None,
                'models':self.settings.public_dict()['models'], 'attempt_timeout':self.settings.attempt_timeout,
                'gateway_authorized':False, 'gateway_url':self.settings.gateway_url,
                'gateway_model':self.settings.gateway_model, 'gateway_effort':self.settings.gateway_effort}

    async def _snapshot(self, job):
        candidates = await asyncio.to_thread(discover_jobs, [job['folder']], owned_paths=self._owned(job['id']))
        source = next((s for s in candidates if s.id == job['id']), None)
        if not source:
            raise ValueError('Job has no readable PDF source')
        return await asyncio.to_thread(snapshot_job, source, self.data_dir/'cache', stable_seconds=self.settings.stable_seconds)

    def _commit(self):
        return subprocess.run(['git','rev-parse','HEAD'], cwd=self.repo_root, check=True, capture_output=True, text=True).stdout.strip()

    async def start(self, job_id, **options):
        lock = self._job_locks.setdefault(job_id, asyncio.Lock())
        async with lock:
            job = self._allowed_job(job_id)
            config = self._config(options)
            snapshot = await self._snapshot(job)
            old = job['current_run']
            if old: await self.publisher.stop(old)
            await self.mutations.run(self.store.set_tracked,job_id, True)
            await self.mutations.run(self.store.set_paused,job_id, False)
            run = await self.mutations.run(self.store.create_run,job_id, snapshot.source_hash, self._commit(), snapshot_dir=snapshot.directory,
                                        force=options.get('force',False), config=config)
            if old and old != run['id'] and old in self.controls:
                self.controls[old].cancel.set()
            return run

    async def refresh_sources(self):
        for job in self.store.list_jobs(tracked_only=True):
            lock = self._job_locks.setdefault(job['id'], asyncio.Lock())
            if lock.locked():
                continue
            async with lock:
                try:
                    job = self._allowed_job(job['id'])
                    current = self.store.get_run(job['current_run']) if job['current_run'] else None
                    candidates = await asyncio.to_thread(discover_jobs,[job['folder']],owned_paths=self._owned(job['id']))
                    source = next((s for s in candidates if s.id == job['id']), None)
                    if not source:
                        raise ValueError('Tracked source unavailable')
                    def digest():
                        manifest = tuple({'path':p.relative_to(source.folder).as_posix(),'sha256':file_hash(p),'size':p.stat().st_size} for p in source.files)
                        return hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                    if current and await asyncio.to_thread(digest) == current['source_hash']:
                        continue
                    snapshot = await self._snapshot(job)
                    if current: await self.publisher.stop(current['id'])
                    run = await self.mutations.run(self.store.create_run,job['id'],snapshot.source_hash,self._commit(),snapshot_dir=snapshot.directory,config=({**current['config'],'gateway_authorized':False} if current else self._config({})))
                    if current and run['id'] != current['id']:
                        if current['id'] in self.controls:
                            self.controls[current['id']].cancel.set()
                        await self.mutations.run(self.store.append_event,run['id'],'source_changed',{'previous_run':current['id'],'paused':job['paused']})
                except (OSError,ValueError) as exc:
                    if job['current_run']:
                        await self.mutations.run(self.store.append_event,job['current_run'],'source_unavailable',{'message':str(exc)})

    def _current(self, job_id):
        job = self._allowed_job(job_id)
        if not job['current_run']:
            raise ValueError('Job has not been started')
        return self.store.get_run(job['current_run'])

    async def pause(self, job_id):
        run = self._current(job_id)
        control = self.controls.get(run['id'])
        if control:
            control.pause.set()
        await self.publisher.stop(run['id'])
        await self.mutations.run(self.store.set_paused,job_id,True)
        run=self._current(job_id)
        if run['id'] in self.controls:
            self.controls[run['id']].pause.set()
            if run['status'] in {'running','publication_pending'}:
                await self.mutations.run(self.store.set_run_status,run['id'],'pause_requested')
        elif run['status'] not in {'completed','cancelled','error','superseded'} and not run['lease']:
            await self.mutations.run(self.store.set_run_status,run['id'],'paused')
        return self.store.get_run(run['id'])

    async def resume(self, job_id):
        run = self._current(job_id)
        if run['id'] in self.active or run['lease']:
            raise ValueError('Wait for worker acknowledgement or process reconciliation')
        if run['checkpoint'].get('pending'):
            raise ValueError('Interrupted request requires explicit gateway reconciliation')
        await self.mutations.run(self.store.resume_run,run['id'])
        self._retry_at.pop(run['id'],None)
        return self.store.get_run(run['id'])

    async def cancel(self, job_id):
        run = self._current(job_id)
        probe=self._probes.get(run['id'])
        if probe:
            probe[0].set(); probe[1].cancel()
            await asyncio.gather(probe[1],return_exceptions=True)
        await self.publisher.stop(run['id'])
        run=self._current(job_id)
        if run['id'] in self.controls:
            self.controls[run['id']].cancel.set()
        if run['status'] not in {'completed','cancelled','error','superseded'}:
            await self.mutations.run(self.store.set_run_status,run['id'],'cancelled')
            await self.mutations.run(self.store.append_event,run['id'],'cancelled',{'requested_at':time.time()})
        return self.store.get_run(run['id'])

    async def use_gateway(self, job_id, *, model=None, effort=None):
        async with self._job_locks.setdefault(job_id,asyncio.Lock()):
            run=self._current(job_id)
            cancel=asyncio.Event()
            self._probes[run['id']]=(cancel,asyncio.current_task())
            try:
                return await self._use_gateway(job_id,model=model,effort=effort,cancel=cancel)
            finally:
                self._probes.pop(run['id'],None)

    async def _use_gateway(self, job_id, *, model=None, effort=None, cancel):
        run = self._current(job_id)
        if run['id'] in self.active or run['lease']:
            raise ValueError('Wait for the previous worker/process to stop')
        if run['status'] not in {'paused','queued','waiting_usage','waiting_fallback','reconciliation_required'}:
            raise ValueError('Gateway selection requires a resumable run')
        config = dict(run['config'])
        model = model or self.settings.gateway_model
        effort = effort or self.settings.gateway_effort
        if not isinstance(model,str) or not model.strip() or len(model)>200 or any(ord(c)<32 for c in model) or effort not in {'medium','high','xhigh','max'}:
            raise ValueError('Select a valid gateway model and effort')
        await self.mutations.run(self.store.set_run_status,run['id'],'waiting_fallback')
        endpoint = self.settings.gateway_url
        gateway = self.gateway_factory(endpoint)
        async with self.model_slot(model,cancel=cancel):
            report = await gateway.probe(model=model,effort=effort,workspace=self.data_dir/'probes',cancel=cancel,emit=self._probe_event,authorized=True)
        if cancel.is_set() or self._closing:
            raise asyncio.CancelledError()
        self.gateway_reports[(endpoint,model,effort)] = asdict(report) | {'ready':report.ready}
        if not report.ready:
            raise ProviderError('gateway_incompatible','Gateway capabilities were not verified for this endpoint/model')
        config.update(gateway_authorized=True,gateway_url=endpoint,gateway_model=model,gateway_effort=effort)
        # Recheck current/terminal/lease/pause atomically after the awaited probe.
        lease = await self.mutations.run(self.store.claim_gateway,run['id'],config,self.owner)
        control = self._control(self.store.get_run(run['id']),lease)
        try:
            if run['checkpoint'].get('pending'):
                await self.mutations.run(reconcile_request,control,disposition='abandon_for_gateway')
        except BaseException:
            await self.mutations.run(self._finish_gateway,run['id'],lease,failed=True)
            raise
        await self.mutations.run(self._finish_gateway,run['id'],lease)
        await self.mutations.run(self.store.append_event,run['id'],'gateway_selected',{'endpoint':endpoint,'model':model,'effort':effort,'capabilities':asdict(report)})
        return self.store.get_run(run['id'])

    def _finish_gateway(self,run_id,lease,*,failed=False):
        run=self.store.get_run(run_id)
        if run['status'] in {'completed','cancelled','error','superseded'}:
            raise ValueError('Run changed while reconciling gateway selection')
        paused=self.store.get_job(run['job_id'])['paused']
        self.store.release_run(run_id,lease,status='paused' if paused else ('reconciliation_required' if failed else 'queued'))

    async def _probe_event(self,event):
        pass  # Probe contains no customer/job data or quota evidence.

    async def providers(self):
        try:
            self._provider = {'status':'ready', **await self.runner.preflight()}
        except ProviderError as exc:
            self._provider = {'status':exc.kind,'message':str(exc)}
        except (OSError,ValueError) as exc:
            self._provider = {'status':'unavailable','message':'Official Claude CLI preflight failed'}
        key = (self.settings.gateway_url,self.settings.gateway_model,self.settings.gateway_effort)
        report = self.gateway_reports.get(key)
        return {'claude':self._provider,'gateway':{'status':('verified' if report['ready'] else 'incompatible') if report else 'not_selected',
                'endpoint':key[0],'model':key[1],'effort':key[2],'capabilities':report,'manual_selection_required':True},
                'gpt':{'status':'unavailable'},'quota':None}

    def _control(self,run,lease):
        config = run['config']
        control = RunControl(self.store,run['id'],lease,run['source_hash'],self.data_dir/'work'/run['id'],slot=self.model_slot,
                          gateway_authorized=config.get('gateway_authorized',False),gateway_model=config.get('gateway_model'),gateway_effort=config.get('gateway_effort'),mutation=self.mutations.run)
        control.slot = lambda model: self.model_slot(model,cancel=control.cancel)
        return control

    async def tick(self):
        if self._closing:
            return
        for run in self.store.list_runs(statuses={'waiting_usage','waiting_output'}):
            if not run['lease'] and time.time() >= self._retry_at.get(run['id'],run['updated']+self.settings.retry_seconds) and not self.store.get_job(run['job_id'])['paused']:
                await self.mutations.run(self.store.set_run_status,run['id'],'queued')
        for run in self.store.list_runs(statuses={'queued'}):
            if run['job_id'] in self._blocked_jobs:
                continue
            if len(self.active) >= self.settings.max_active_jobs:
                break
            if self.store.get_job(run['job_id'])['paused']:
                await self.mutations.run(self.store.set_run_status,run['id'],'paused'); continue
            if any(self.store.get_run(identity)['job_id']==run['job_id'] for identity in self.active):
                continue
            try:
                self._allowed_job(run['job_id'])
            except ValueError:
                continue
            lease = await self.mutations.run(self.store.claim_run,run['id'],self.owner)
            if lease:
                control = self._control(run,lease)
                self.controls[run['id']] = control
                self.active[run['id']] = asyncio.create_task(self._work(run,control))

    async def _work(self,run,control):
        started = time.monotonic()
        await self.mutations.run(self.store.append_event,run['id'],'worker_started',{'provider':'9router' if control.gateway_authorized else 'claude'})
        try:
            if run['publication']:
                await control.boundary()
                await self.publisher.run(run,control,timeout=self.settings.output_timeout)
            elif run['checkpoint'].get('export'):
                exported=run['checkpoint']['export']['files']
                await control.boundary()
                await self.publisher.run(run,control,files={k:Path(v) for k,v in exported.items()},
                    parts_destination=Path(run['config']['parts_destination']) if run['config'].get('parts_destination') else None,timeout=self.settings.output_timeout)
            else:
                if not control.gateway_authorized:
                    try:
                        self._provider = {'status':'ready',**await self.runner.preflight()}
                    except ProviderError:
                        raise
                async with self._repo_locks.setdefault(run['repo_commit'],asyncio.Lock()):
                    repo = await asyncio.to_thread(PinnedRepository.pin,self.repo_root,self.data_dir/'engines'/run['repo_commit'],run['repo_commit'])
                config = run['config']
                gateway = self.gateway_factory(config['gateway_url']) if control.gateway_authorized else None
                pipeline = self.pipeline_factory(repo,self.runner,gateway=gateway,models=config.get('models'),attempt_timeout=config.get('attempt_timeout',1200),difficulty=config.get('difficulty','auto'))
                result = await pipeline.run(run['snapshot_dir'],control,job_name=self.store.get_job(run['job_id'])['name'],individual=config.get('individual',False))
                await control.boundary()
                await self.publisher.run(run,control,files=result.staged_files,
                                        parts_destination=Path(config['parts_destination']) if config.get('parts_destination') else None,timeout=self.settings.output_timeout)
        except Paused:
            await self._release_if_current(run,control,'paused')
        except asyncio.CancelledError:
            # Application shutdown is resumable; a pending accepted request stays blocked.
            current = self.store.get_run(run['id'])
            if current['status'] not in {'superseded','cancelled','completed','error'}:
                status = 'reconciliation_required' if current['checkpoint'].get('pending') else ('paused' if self.store.get_job(run['job_id'])['paused'] else 'queued')
                await self._release_if_current(run,control,status)
        except ProviderError as exc:
            status = 'reconciliation_required' if exc.outcome=='unknown' else ('waiting_usage' if exc.kind in {'rate_limit','usage_limit','rate_limited'} else 'waiting_fallback')
            await self._release_if_current(run,control,status,str(exc))
        except (PipelineError,Exception) as exc:
            current = self.store.get_run(run['id'])
            if current['status'] not in {'superseded','cancelled','completed','error'}:
                if control.pause.is_set() or self.store.get_job(run['job_id'])['paused']:
                    await self._release_if_current(run,control,'paused')
                elif current['publication'] or isinstance(exc,PublicationError) or current['checkpoint'].get('export'):
                    await self._release_if_current(run,control,'waiting_output',str(exc))
                elif getattr(exc,'kind',None)=='reconciliation_required' or current['checkpoint'].get('pending'):
                    await self._release_if_current(run,control,'reconciliation_required',str(exc))
                else:
                    await self.mutations.run(self.store.set_run_status,run['id'],'error',error=str(exc))
        finally:
            await self.mutations.run(self.store.append_event,run['id'],'worker_stopped',{'elapsed_seconds':time.monotonic()-started,'status':self.store.get_run(run['id'])['status']})
            self.controls.pop(run['id'],None); self.active.pop(run['id'],None)

    async def _release_if_current(self,run,control,status,error=None):
        current = self.store.get_run(run['id'])
        if current['status'] in {'superseded','cancelled','completed','error'}:
            return
        released = await self.mutations.run(self.store.release_run,run['id'],control.lease,status=status,error=error,if_current=True)
        if not released:
            return
        await self.mutations.run(self.store.append_event,run['id'],'worker_state',{'status':status,'message':error})
        if status in {'waiting_usage','waiting_output'}:
            self._retry_at[run['id']] = time.time()+self.settings.retry_seconds

    async def _loop(self):
        next_scan = 0
        while not self._closing:
            try:
                await self.tick()
                if time.monotonic() >= next_scan:
                    await self.refresh_sources()
                    next_scan = time.monotonic()+self.settings.scan_interval
                self.last_error = None
            except Exception as exc:
                self.last_error = str(exc)
            await asyncio.sleep(.1)

    def _metrics(self,current):
        durations={'active_seconds':0.0,'paused_seconds':0.0,'waiting_seconds':0.0}
        if not current: return durations,{},{}
        with self.store._connect() as db:
            events=db.execute("SELECT kind,payload,created FROM events WHERE run_id=? AND kind IN ('worker_started','worker_stopped','worker_state','recovered') ORDER BY id",(current['id'],)).fetchall()
            overhead_rows=db.execute("SELECT u.metrics FROM usage u JOIN events e ON e.run_id=u.run_id AND e.event_key=u.event_key WHERE u.run_id=? AND e.kind='usage' AND json_extract(e.payload,'$.code') IS NULL",(current['id'],)).fetchall()
        state='queued'; since=current['created']
        end=min(time.time(),current['updated']) if current['status'] in {'completed','cancelled','error','superseded'} else time.time()
        def accrue(until):
            until=min(until,end)
            key='active_seconds' if state in {'running','pause_requested'} else ('paused_seconds' if state=='paused' else 'waiting_seconds' if state in {'waiting_usage','waiting_fallback','waiting_output','reconciliation_required'} else None)
            if key: durations[key]+=max(0,until-since)
        for index,row in enumerate(events):
            payload=json.loads(row['payload'])
            # Legacy stops lacked status. Keep the preceding state until the next
            # worker starts; only the final stop may use the run's current state.
            new='running' if row['kind']=='worker_started' else payload.get('status')
            if row['kind']=='worker_stopped' and not new and index==len(events)-1:
                new=current['status']
            if new: accrue(row['created']); since=row['created']; state=new
        accrue(time.time())
        overhead={}
        for row in overhead_rows:
            for key,value in json.loads(row['metrics']).items(): overhead[key]=overhead.get(key,0)+value
        return durations,self.store.usage(current['id']),overhead

    def job(self,job_id,*,summary=False):
        job=self.store.get_job(job_id)
        summaries=self.store.run_summaries(job_id=job_id,run_id=job['current_run'] if summary else None,limit=1 if summary else 100)
        current=next((r for r in summaries if r['id']==job['current_run']),None)
        counts=self.store.part_counts(current['id']) if current else {}
        durations,usage,overhead=self._metrics(current)
        # The dashboard table never opens source/output files or reads checkpoints.
        result={**job,'status':current['status'] if current else 'discovered','run':current,
                'technical_counts':counts,'usage':usage,'durations':durations,
                'provider':'9router' if current and current['config'].get('gateway_authorized') else 'claude',
                'blocked_reason':'Previous process identity cannot be verified' if job_id in self._blocked_jobs else None,
                'shared_overhead_usage':overhead}
        if summary:
            with self.store._connect() as db:
                row=db.execute('SELECT reviewed FROM reviews WHERE run_id=? ORDER BY id DESC LIMIT 1',(current['id'] if current else '',)).fetchone()
            result['reviewed']=bool(row and row['reviewed'] and current['status']=='completed')
            result['review_verification']='recorded_revision_only'
            return result
        parts=self.store.parts(current['id']) if current else []
        reviews=self.store.reviews(current['id']) if current else []
        files=self.files(job_id)
        outputs=[f for f in files if f['kind']=='output' and f['current']]
        revision=[{'path':f['path'],'sha256':f['sha256']} for f in outputs]
        matching=[r for r in reviews if current and r['source_hash']==current['source_hash'] and sorted(r['outputs'],key=lambda x:x['path'])==sorted(revision,key=lambda x:x['path'])]
        result.update(runs=summaries,parts=parts,reviews=reviews,files=files,
                      reviewed=bool(current and current['status']=='completed' and outputs and matching and matching[-1]['reviewed']),
                      review_verification='current_files_verified')
        return result

    def jobs(self):
        return [self.job(job['id'],summary=True) for job in self.store.list_jobs()]

    def files(self,job_id):
        job = self.store.get_job(job_id)
        current = self.store.get_run(job['current_run']) if job['current_run'] else None
        records = []
        def add(kind,path,run_id=None,expected=None,status='source'):
            path = Path(path)
            exists = path.is_file() and not path.is_symlink()
            try:
                actual = file_hash(path) if exists else None
            except OSError:
                actual = None
                exists = False
            owner = self.store.get_run(run_id) if run_id else None
            valid = bool(kind!='output' or (owner and actual==expected and (
                (owner['status']=='completed' and status=='current') or status=='archived')))
            is_current = bool(valid and (not owner or (current and owner['id']==current['id'])))
            identity = hashlib.sha256(f'{kind}|{run_id}|{path}'.encode()).hexdigest()
            page_count=None
            if kind=='source' and exists and path.suffix.lower()=='.pdf':
                try:
                    import fitz
                    with fitz.open(path) as pdf: page_count=len(pdf)
                except Exception: pass
            records.append({'page_count':page_count,'pages_url':f'/api/jobs/{job_id}/files/{identity}/pages/{{page}}' if page_count else None,'id':identity,'kind':kind,'name':path.name,'path':str(path),'run_id':run_id,'sha256':expected or actual,
                            'exists':exists,'hash_matches':actual==expected if expected else None,'status':status,'current':is_current,
                            'stale':bool(kind=='output' and not is_current),'download_url':f'/api/jobs/{job_id}/files/{identity}' if exists and (not expected or actual==expected) and (kind!='output' or valid) else None})
        if current and current['snapshot_dir']:
            for entry in json.loads((current['snapshot_dir']/'manifest.json').read_text()):
                add('source',contained_path(current['snapshot_dir'],entry['path']),current['id'],entry['sha256'])
            workspace = self.data_dir/'work'/current['id']
            if workspace.exists():
                for image in (workspace/'pages').glob('*.png'):
                    add('page',image,current['id'])
                # Evidence renderer's original page names are host owned.
                for image in (workspace/'render').glob('*.png'):
                    add('page',image,current['id'])
        else:
            try:
                self._allowed_job(job_id)
                for source in discover_jobs([job['folder']],owned_paths=self._owned(job_id)):
                    if source.id==job_id:
                        for path in source.files: add('source',path)
            except (OSError,ValueError):
                pass
        for output in self.store.outputs(job_id=job_id,current_only=False):
            path = output['archive_path'] if output['status']=='archived' else output['path']
            if path:
                add('output',path,output['run_id'],output['sha256'],output['status'])
        return records

    def file_path(self,job_id,file_id):
        job=self.store.get_job(job_id)
        if not any(job['folder'].is_relative_to(root) for root in self.settings.roots):
            raise ValueError('Job is outside configured source roots')
        record = next((f for f in self.files(job_id) if f['id']==file_id and f['download_url']),None)
        if not record:
            raise KeyError('File unavailable')
        path = Path(record['path'])
        if record['kind']=='output':
            run = self.store.get_run(record['run_id']); config=run['config']
            job = self.store.get_job(job_id)
            roots = [self.data_dir/'history'/job_id/run['id']] if record['status']=='archived' else [job['folder']]
            if record['status']!='archived' and config.get('parts_destination'): roots.append(Path(config['parts_destination']))
        else:
            roots = [self.store.get_job(job_id)['folder'],self.data_dir/'cache',self.data_dir/'work']
        for root in roots:
            if path.is_relative_to(root) and path != root:
                return contained_path(root,path.relative_to(root)),record
        raise ValueError('File escaped its job scope')

    async def review(self,job_id,*,reviewer='local user',note='',run_id=None,reviewed=True):
        run = self._current(job_id)
        if run_id != run['id'] or run['status']!='completed':
            raise ValueError('Review must name the completed current run')
        outputs = [f for f in self.files(job_id) if f['kind']=='output' and f['run_id']==run['id']]
        if not outputs or any(not f['current'] for f in outputs):
            raise ValueError('Current output revision is missing, changed or unpublished')
        await self.mutations.run(self.store.record_review,run['id'],reviewer,note,reviewed=reviewed)
        return self.job(job_id)

    async def open_folder(self,job_id,*,target='source'):
        job=self._allowed_job(job_id)
        if target=='source': path=job['folder']
        elif target=='individual':
            run=self._current(job_id)
            path=Path(run['config'].get('parts_destination') or job['folder']/'parts_dxf')
            if not run['config'].get('individual') or not path.is_dir():
                raise ValueError('Individual output folder unavailable')
            contained_path(path,'folder-scope-check')
        else: raise ValueError('Unknown folder target')
        await asyncio.to_thread(self.folder_opener,path)
        return {'opened':True,'target':target}

    @staticmethod
    def _open_folder(path):
        if os.name=='nt': os.startfile(str(path))
        elif __import__('sys').platform=='darwin': subprocess.Popen(['open',str(path)])
        else: subprocess.Popen(['xdg-open',str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
