"""Owned, interruptible OS process boundary around the existing Publisher journal.

No geometry or provider work occurs here. Durable identity is recorded before stdin
allows filesystem work. Termination stops this client; it cannot roll back SMB.
"""
from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from LuanAppTools.ai.claude import process_identity
from LuanAppTools.ai.protocol import cancellable


class PublicationError(RuntimeError):
    pass


class OwnedPublisher:
    def __init__(self, store, archive_dir, repo_root, *, command=None, mutation=None):
        self.store=store
        self.mutation=mutation
        self.archive_dir=Path(archive_dir)
        self.repo_root=Path(repo_root)
        self.children={}
        self.command=tuple(command or (sys.executable,'-m','LuanAppTools.service.publication','--worker'))

    async def _write(self,operation,*args,**kwargs):
        if self.mutation is None: return operation(*args,**kwargs)
        return await self.mutation(operation,*args,**kwargs)

    def signal_all(self):
        for process,_ in list(self.children.values()):
            if process.returncode is None: process.kill()

    async def stop(self,run_id):
        child=self.children.get(run_id)
        if not child: return
        process,done=child
        if process.returncode is None:
            process.kill()  # The still-owned asyncio subprocess handle, never a rediscovered PID.
        await process.wait()
        await done.wait()  # Exit audit must commit before a control action writes state.

    async def run(self,run,control,*,files=None,parts_destination=None,timeout=120):
        if control.cancel.is_set(): raise asyncio.CancelledError()
        control.workspace.mkdir(parents=True,exist_ok=True)
        result_path=control.workspace/('publication-'+uuid.uuid4().hex+'.json')
        kwargs={'start_new_session':True} if os.name!='nt' else {'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP}
        process=await asyncio.create_subprocess_exec(*self.command,
                    cwd=self.repo_root,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,**kwargs)
        done=asyncio.Event(); identity=None
        self.children[run['id']]=(process,done)
        try:
            identity=process_identity(process.pid,control.workspace)
            await self._write(self.store.append_event,run['id'],'publication_process_started',{'process':identity})
            payload={'db_path':str(self.store.db_path),'archive_dir':str(self.archive_dir),'run_id':run['id'],
                     'lease':control.lease,'source_hash':run['source_hash'],'files':{k:str(v) for k,v in files.items()} if files is not None else None,
                     'parts_destination':str(parts_destination) if parts_destination else None,'result_path':str(result_path)}
            from LuanAppTools.ai.protocol import ProviderError
            try:
                await cancellable(process.communicate(json.dumps(payload).encode()),control.cancel,timeout)
            except ProviderError as exc:
                raise PublicationError('Output copy deadline exhausted; validated local export/journal retained') from exc
            if not result_path.is_file():
                raise PublicationError('Output copy process stopped before confirmation; retry uses the durable journal and validated local export')
            result=json.loads(result_path.read_text())
            if not result['ok']: raise PublicationError(result['message'])
            return result['result']
        finally:
            if process.returncode is None: process.kill()
            await process.wait()
            try:
                if identity:
                    await self._write(self.store.append_event,run['id'],'publication_process_exited',{'process':identity,'returncode':process.returncode})
            finally:
                self.children.pop(run['id'],None); done.set(); result_path.unlink(missing_ok=True)


def worker():
    """Host-owned stdin only; not exposed through HTTP or AI tools."""
    from LuanAppTools.core.store import Store
    from LuanAppTools.core.publisher import Publisher
    payload=json.loads(sys.stdin.read())
    store=Store(Path(payload['db_path']))
    publisher=Publisher(store,Path(payload['archive_dir']))
    try:
        if payload['files'] is None:
            result=publisher.retry(payload['run_id'],payload['lease'])
        else:
            result=publisher.publish(payload['run_id'],payload['lease'],payload['source_hash'],
                      {k:Path(v) for k,v in payload['files'].items()},
                      parts_destination=Path(payload['parts_destination']) if payload['parts_destination'] else None)
        response={'ok':True,'result':result}
    except Exception as exc:
        response={'ok':False,'message':str(exc)}
    Path(payload['result_path']).write_text(json.dumps(response))


if __name__=='__main__' and sys.argv[1:]==['--worker']:
    worker()
