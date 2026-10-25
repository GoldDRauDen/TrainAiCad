"""Service-owned SQLite writer attempts; lock waits never occupy the event loop.

Each synchronous attempt uses the Store's short busy timeout. SQLITE_BUSY retries
are awaitable/cancellable. Cancelling a caller first drains its current attempt;
close joins the private executor after all owned callers finish, so no abandoned
mutation can commit after lifecycle ownership is released.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import sqlite3


class AsyncMutations:
    def __init__(self):
        self._executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='luanapp-sqlite')
        self._calls=set()
        self._closing=False

    async def run(self,operation,*args,**kwargs):
        if self._closing: raise RuntimeError('Service mutation boundary is closed')
        caller=asyncio.current_task()
        self._calls.add(caller)
        try:
            while True:
                if self._closing: raise RuntimeError('Service mutation boundary is closing')
                future=asyncio.get_running_loop().run_in_executor(self._executor,partial(operation,*args,**kwargs))
                try:
                    return await asyncio.shield(future)
                except asyncio.CancelledError:
                    # Executor work cannot be killed. Wait for this bounded SQLite
                    # attempt before propagating cancellation; never retry it later.
                    while not future.done():
                        try: await asyncio.shield(future)
                        except asyncio.CancelledError: continue
                        except Exception: break
                    if future.done() and not future.cancelled(): future.exception()
                    raise
                except sqlite3.OperationalError as exc:
                    if getattr(exc,'sqlite_errorcode',None) not in {sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED}:
                        raise
                    await asyncio.sleep(.01)
        finally:
            self._calls.discard(caller)

    async def close(self):
        self._closing=True
        calls=list(self._calls-{asyncio.current_task()})
        if calls: await asyncio.gather(*calls,return_exceptions=True)
        self._executor.shutdown(wait=True)
