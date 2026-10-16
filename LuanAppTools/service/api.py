"""Loopback-only, same-origin API. Mutations require the local session token."""
from contextlib import asynccontextmanager
import asyncio
import hmac
import ipaddress
from pathlib import Path
import secrets
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, Query
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from LuanAppTools.ai.protocol import ProviderError
from LuanAppTools.cad.pipeline import PipelineError
from LuanAppTools.cad.preview import render_dxf
from .controller import ApplicationService


class Body(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class StartBody(Body):
    difficulty: Literal['auto','easy','medium','hard'] | None = None
    individual: bool | None = None
    parts_destination: str | None = None
    force: bool = False

class GatewayBody(Body):
    model: str | None = None
    effort: Literal['medium','high','xhigh','max'] | None = None

class ReviewBody(Body):
    run_id: str
    reviewed: bool = True
    reviewer: str = Field(default='local user', min_length=1, max_length=200)
    note: str = Field(default='', max_length=10000)

class FolderBody(Body):
    target: Literal['source','individual'] = 'source'

class SettingsBody(Body):
    roots: list[str] | None = None
    max_active_jobs: int | None = None
    max_ai_calls: int | None = None
    max_opus_calls: int | None = None
    scan_interval: float | None = None
    stable_seconds: float | None = None
    attempt_timeout: float | None = None
    gateway_url: str | None = None
    gateway_model: str | None = None
    gateway_effort: Literal['medium','high','xhigh','max'] | None = None
    default_difficulty: Literal['auto','easy','medium','hard'] | None = None
    individual_output: bool | None = None
    individual_destination: str | None = None
    retry_seconds: float | None = None
    shutdown_seconds: float | None = None
    output_timeout: float | None = None
    models: dict[str,dict[str,str]] | None = None


def _loopback(host):
    if host == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def create_app(data_dir: Path, repo_root: Path, start_scheduler: bool = True, *, service: ApplicationService | None = None):
    service = service or ApplicationService(data_dir,repo_root)
    token = secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(app):
        await service.open(start_scheduler=start_scheduler)
        try:
            yield
        finally:
            await service.close()

    app = FastAPI(title='LuanAppTools local API',version='1',lifespan=lifespan)
    app.state.service = service

    @app.middleware('http')
    async def boundary(request,call_next):
        host = request.headers.get('host','')
        try:
            parsed = urlsplit('//'+host)
            valid = bool(parsed.hostname and _loopback(parsed.hostname) and not parsed.username and not parsed.password and not parsed.path and not parsed.query and not parsed.fragment)
            parsed.port
        except ValueError:
            valid = False
        if not valid:
            return JSONResponse({'error':{'code':'host_forbidden','message':'Use the loopback app address'}},403)
        origin = request.headers.get('origin')
        if origin and origin != f'{request.url.scheme}://{host}':
            return JSONResponse({'error':{'code':'origin_forbidden','message':'Same-origin requests only'}},403)
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'error':{'code':'origin_forbidden','message':'Same-origin requests only'}},403)
        if request.method not in {'GET','HEAD','OPTIONS'}:
            if not hmac.compare_digest(request.headers.get('x-luan-token',''),token):
                return JSONResponse({'error':{'code':'token_required','message':'Refresh the app session and retry'}},403)
            if request.headers.get('content-type','') != 'application/json':
                return JSONResponse({'error':{'code':'json_required','message':'Content-Type must be exactly application/json'}},415)
        response = await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        return JSONResponse({'error':{'code':'invalid_json','message':'Request body or query does not match the API schema'}},422)

    @app.exception_handler(KeyError)
    async def not_found(request,exc):
        return JSONResponse({'error':{'code':'not_found','message':'Job, run or file not found'}},404)

    @app.exception_handler(ValueError)
    async def invalid(request,exc):
        return JSONResponse({'error':{'code':'invalid_request','message':str(exc)}},409)

    @app.exception_handler(ProviderError)
    async def provider_error(request,exc):
        return JSONResponse({'error':{'code':exc.kind,'message':str(exc),'outcome':exc.outcome}},409)

    @app.exception_handler(PipelineError)
    async def pipeline_error(request,exc):
        return JSONResponse({'error':{'code':exc.kind,'message':str(exc)}},409)

    @app.exception_handler(OSError)
    async def filesystem_error(request,exc):
        return JSONResponse({'error':{'code':'filesystem_unavailable','message':'Folder/file access failed; check the local or LAN connection and permissions'}},409)

    @app.get('/api/health')
    async def health():
        return {'status':'ok','mutation_token':token,'scheduler_running':service._scheduler is not None,
                'active_jobs':len(service.active),'active_ai_calls':service._ai_active,'active_opus_calls':service._opus_active,
                'last_error':service.last_error,'roots':[{'path':str(root),'available':root.is_dir()} for root in service.settings.roots]}

    @app.get('/api/settings')
    async def settings():
        return service.settings.public_dict()

    @app.put('/api/settings')
    async def put_settings(body:SettingsBody):
        return service.update_settings(body.model_dump(exclude_unset=True))

    @app.post('/api/scan')
    async def scan(body:Body):
        return jsonable_encoder(await service.scan())

    @app.get('/api/jobs')
    async def jobs():
        return jsonable_encoder({'jobs':service.jobs()})

    @app.get('/api/jobs/{job_id}')
    async def job(job_id:str):
        return jsonable_encoder(service.job(job_id))

    @app.post('/api/jobs/{job_id}/start')
    async def start(job_id:str,body:StartBody):
        options=body.model_dump(exclude_none=True,exclude_unset=True)
        return jsonable_encoder({'run':service.store.public_run(await service.start(job_id,**options))})

    @app.post('/api/jobs/{job_id}/pause')
    async def pause(job_id:str,body:Body):
        return jsonable_encoder({'run':service.store.public_run(await service.pause(job_id))})

    @app.post('/api/jobs/{job_id}/resume')
    async def resume(job_id:str,body:Body):
        return jsonable_encoder({'run':service.store.public_run(await service.resume(job_id))})

    @app.post('/api/jobs/{job_id}/cancel')
    async def cancel(job_id:str,body:Body):
        return jsonable_encoder({'run':service.store.public_run(await service.cancel(job_id))})

    @app.post('/api/jobs/{job_id}/use-gateway')
    async def gateway(job_id:str,body:GatewayBody):
        return jsonable_encoder({'run':service.store.public_run(await service.use_gateway(job_id,**body.model_dump()))})

    @app.post('/api/jobs/{job_id}/review')
    async def review(job_id:str,body:ReviewBody):
        return jsonable_encoder(await service.review(job_id,**body.model_dump()))

    @app.get('/api/jobs/{job_id}/events')
    async def events(job_id:str,after:int=Query(0,ge=0),run_id:str|None=None):
        job=service.store.get_job(job_id)
        run_id=run_id or job['current_run']
        if not run_id: return {'events':[],'next_after':after,'run_id':None}
        run=service.store.get_run(run_id)
        if run['job_id']!=job_id: raise KeyError('Run is outside job')
        rows=service.store.events_since(run_id,after)
        allowed={'stage','code','request_id','session_id','type','model','effort','metrics','cumulative','status','message','elapsed_seconds','attempts','provider','endpoint','previous_run','paused','recovered','returncode','requested_at'}
        rows=[{**row,'payload':{k:(v[:4096] if isinstance(v,str) else v) for k,v in row['payload'].items() if k in allowed}} for row in rows]
        return {'events':rows,'next_after':rows[-1]['id'] if rows else after,'run_id':run_id}

    @app.get('/api/jobs/{job_id}/files')
    async def files(job_id:str):
        return {'files':service.files(job_id)}

    @app.get('/api/jobs/{job_id}/files/{file_id}')
    async def file(job_id:str,file_id:str):
        path,record=service.file_path(job_id,file_id)
        return FileResponse(path,filename=record['name'])

    @app.get('/api/jobs/{job_id}/files/{file_id}/pages/{page}')
    async def page_image(job_id:str,file_id:str,page:int):
        path,record=service.file_path(job_id,file_id)
        if record['kind']!='source' or path.suffix.lower()!='.pdf' or page<1:
            raise KeyError('Not an original PDF page')
        destination=service.data_dir/'previews'/job_id/(file_id+f'-page-{page}.png')
        def render():
            import fitz
            with fitz.open(path) as doc:
                if page>len(doc): raise KeyError('Page does not exist')
                destination.parent.mkdir(parents=True,exist_ok=True)
                doc[page-1].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(destination)
        await asyncio.to_thread(render)
        return FileResponse(destination,media_type='image/png')

    @app.get('/api/jobs/{job_id}/preview')
    async def previews(job_id:str):
        return {'previews':[{'file_id':f['id'],'name':f['name'],'current':f['current'],
                             'url':f'/api/jobs/{job_id}/preview/{f["id"]}'} for f in service.files(job_id)
                            if f['download_url'] and f['name'].lower().endswith('.dxf')]}

    @app.get('/api/jobs/{job_id}/preview/{file_id}')
    async def preview(job_id:str,file_id:str):
        path,record=service.file_path(job_id,file_id)
        if path.suffix.lower()!='.dxf': raise KeyError('Not a DXF')
        destination=service.data_dir/'previews'/job_id/(file_id+'.svg')
        await asyncio.to_thread(render_dxf,path,destination)
        return FileResponse(destination,media_type='image/svg+xml',headers={'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; sandbox"})

    @app.get('/api/providers')
    async def providers():
        return await service.providers()

    @app.post('/api/jobs/{job_id}/open-folder')
    async def open_folder(job_id:str,body:FolderBody):
        return await service.open_folder(job_id,**body.model_dump())

    dist=Path(repo_root)/'LuanAppTools'/'frontend'/'dist'
    if (dist/'index.html').is_file():
        app.mount('/',StaticFiles(directory=dist,html=True),name='frontend')
    return app
