import asyncio
from asyncio import new_event_loop, start_server, Event
from asyncio import StreamReader, StreamWriter
from hakunet.utils import *


#Export
__all__ = ["HakuServer"]


#Type Aliases
EventHandler = Callable[["HakuServer.Context", Any], Awaitable[None]]
Transaction = Callable[["HakuServer.TRXContext"], Awaitable[None]]
Response = Callable[[Any], Awaitable[Any]]


class HakuServer:
    class Context:
        def __init__(
            self, 
            server: "HakuServer", 
            reader: StreamReader, 
            writer: StreamWriter,
        ):
            self.server = server
            self.reader = reader
            self.writer = writer
        
        def close(self):
            self.writer.close()
        
        def is_closing(self):
            return self.writer.is_closing()
        
        async def send(self, data):
            await write_with_len_async(self.writer, data)
        
        async def emit(
            self, 
            event: str, *args, 
            broadcast=False, **kwargs,
        ):
            if broadcast:
                await self.server.emit(event, *args, **kwargs)
            else:
                await self.send([event, args, kwargs])
    
    class TRXContext:
        def __init__(
            self, 
            server: "HakuServer", 
            tid: int, 
            ctx: "HakuServer.Context"
        ):
            self.server = server
            self.tid = tid
            self.ctx = ctx
        
        async def send(self, data):
            await self.ctx.send(['tsc', self.tid, data])
        
        async def read(self):
            await self.server._t_event[self.tid].wait()
            data = self.server._t_mes_queue[self.tid].pop(0)
            if self.server._t_mes_queue[self.tid] == []:
                self.server._t_event[self.tid].clear()
            return data
    
    def __init__(self, host: str, port: int|str):
        self.host = host
        self.port = port
        
        self.server: asyncio.Server
        self.server_starter = start_server(
            self.handle_client, host, port
        )
        
        self.contexts: list[HakuServer.Context] = []
        self.event_handlers: dict[str, EventHandler] = {}
        self.transactions: dict[str, Transaction] = {}
        self.responses: dict[str, Response] = {}
        
        self._t_event: dict[int, Event] = {}
        self._t_mes_queue: dict[int, list[Any]] = {}
    
    def run(self):
        loop = new_event_loop()
        try:
            loop.run_until_complete(self.coro())
        except KeyboardInterrupt:
            pass
            
    async def coro(self):
        self.server = await self.server_starter
        async with self.server as server:
            await server.serve_forever()
    
    async def handle_client(
        self, 
        reader: StreamReader, 
        writer: StreamWriter,
    ):
        new_ctx = HakuServer.Context(self, reader, writer)
        self.contexts.append(new_ctx)
        
        while not new_ctx.is_closing():
            data = await read_msg(reader)
            if data is None:
                break
            
            match data:
                case ['tsc', int(tid), data]:
                    if (tid in self._t_event 
                        and tid in self._t_mes_queue):
                        self._t_mes_queue[tid].append(data)
                        self._t_event[tid].set()
                
                case ['tsc_st', int(tid), str(ttype)]:
                    self._t_event[tid] = Event()
                    self._t_mes_queue[tid] = []
                    new_tsc = HakuServer.TRXContext(
                        self, tid, new_ctx
                    )
                    asyncio.ensure_future(
                        self.transactions[ttype](new_tsc)
                    )
                
                case ['call', str(method), int(cid), args, kwargs]:
                    await new_ctx.send([
                        'resp', cid, 
                        await self.responses[method](*args, **kwargs)
                    ])
                
                case [str(event), args, kwargs]:
                    if event in self.event_handlers:
                        handler = self.event_handlers[event]
                        await handler(new_ctx, *args, **kwargs)
        
        new_ctx.close()
        new_ctx_list = []
        
        for c in self.contexts:
            if not c.is_closing():
                new_ctx_list.append(c)
        self.contexts = new_ctx_list
    
    def on_event(self, event: str):
        def decorator(func: EventHandler) -> EventHandler:
            self.event_handlers[event] = func
            return func
        return decorator
    
    def register_event(self, event: str, func: EventHandler):
        self.event_handlers[event] = func
    
    def on_transaction(self, tsc: str):
        def decorator(func: Transaction) -> Transaction:
            async def wrapper(ctx: HakuServer.TRXContext):
                try:
                    await func(ctx)
                except ConnectionError:
                    print(
                        f'Transaction {ctx.tid} Stopped'
                        ', because client is disconnected.'
                    )
                    pass
                del self._t_event[ctx.tid]
                del self._t_mes_queue[ctx.tid]
            self.transactions[tsc] = wrapper
            return wrapper
        return decorator
    
    def register_transaction(self, tsc: str, func: Transaction):
        async def wrapper(ctx: HakuServer.TRXContext):
            try:
                await func(ctx)
            except ConnectionError:
                print(
                    f'Transaction {ctx.tid} Stopped'
                    ', because client is disconnected.'
                )
                pass
            del self._t_event[ctx.tid]
            del self._t_mes_queue[ctx.tid]
        self.transactions[tsc] = wrapper
    
    def on_call(self, rq: str):
        def decorator(resp: Response) -> Response:
            self.responses[rq] = resp
            return resp
        return decorator
    
    def register_call(self, rq: str, func: Response):
        self.responses[rq] = func
    
    async def emit(self, event, *args, **kwargs):
        for c in self.contexts:
            await c.emit(event, *args, **kwargs)