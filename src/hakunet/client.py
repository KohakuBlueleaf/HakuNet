from typing import *

import asyncio

from time import time_ns
from asyncio import open_connection, sleep
from asyncio import Event, StreamWriter, StreamReader

from hakunet.protocol import *


#Export
__all__ = ['HakuClient']


#Type Aliases
EventHandler = Callable[["HakuClient.Context", Any], Awaitable[None]]
Transaction = Callable[["HakuClient.TRXContext", Any], Awaitable[Any]]



class HakuClient:
    class Context:
        def __init__(
            self, 
            writer: StreamWriter,
            protocol: BaseProtocol,
        ):
            self.writer = writer
            self.protocol = protocol
        
        async def close(self):
            self.writer.close()
            await self.writer.wait_closed()
        
        def is_closing(self):
            return self.writer.is_closing()
        
        async def send(self, data):
            await self.protocol.write_obj(
                self.writer, data
            )
        
        def emit(self, event: str, *args, **kwargs):
            self.send([event, args, kwargs])
    
    class TRXContext:
        def __init__(
            self, 
            tid: int, 
            ttype: str, 
            client: "HakuClient", 
            writer: StreamWriter
        ):
            self.tid = tid
            self.ttype = ttype
            self.client = client
            self.writer = writer
            self.m_index = 0
        
        async def start(self):
            await self.client.protocol.write_obj(
                self.writer,
                ['tsc_st', self.tid, self.ttype],
            )
        
        async def send(self, data):
            await self.client.protocol.write_obj(
                self.writer,
                ['tsc', self.tid, data],
            )
        
        async def read(self):
            await self.client._trx_event[self.tid].wait()
            data = self.client._trx_mes_queue[self.tid].pop(0)
            if self.client._trx_mes_queue[self.tid] == []:
                self.client._trx_event[self.tid].clear()
            return data
    
    def __init__(
        self, 
        host: str, 
        port: str|int,
        protocol: BaseProtocol = PickleProtocol(),
    ):
        self.host = host
        self.port = port
        self.context: HakuClient.Context
        self.protocol = protocol
        
        self.handlers: dict[str, EventHandler] = {}
        self.transactions: dict[str, Transaction] = {}
        
        self._trx_event: dict[int, Event] = {}
        self._trx_mes_queue: dict[int, list[Any]] = {}
        self._resp_event: dict[int, Event] = {}
        self._resp_mes: dict[int, Any] = {}
    
    async def __aenter__(self):
        reader, writer = await open_connection(self.host, self.port)
        self.handle_client(reader, writer)
        await sleep(0.01)
    
    async def __aexit__(self, exc_type, exc, tb):
        await sleep(0.1)
        await self.context.close()
    
    async def connect(self):
        reader, writer = await open_connection(self.host, self.port)
        self.handle_client(reader, writer)
    
    async def close(self):
        await self.context.close()
    
    def is_closing(self):
        return self.context.is_closing
    
    def on_event(self, event):
        def decorator(func):
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            self.handlers[event] = wrapper
            return wrapper
        return decorator
    
    def register_event(self, event, func):
        self.handlers[event] = func
    
    def on_transaction(self, ttype: str):
        def decorator(func: Transaction) -> Transaction:
            async def wrapper(*args, **kwargs):
                tsc = HakuClient.TRXContext(
                    time_ns(), ttype, self, self.context.writer
                )
                self._trx_event[tsc.tid] = Event()
                self._trx_mes_queue[tsc.tid] = []
                await tsc.start()
                res = await func(tsc, *args, **kwargs)
                del self._trx_event[tsc.tid]
                del self._trx_mes_queue[tsc.tid]
                return res
            
            setattr(self, ttype, wrapper)
            self.transactions[ttype] = wrapper
            return wrapper
        
        return decorator
    
    def register_transaction(self, ttype: str, func: Transaction):
        async def wrapper(*args, **kwargs):
            tsc = HakuClient.TRXContext(
                time_ns(), ttype, self, self.context.writer
            )
            self._trx_event[tsc.tid] = Event()
            self._trx_mes_queue[tsc.tid] = []
            await tsc.start()
            res = await func(tsc, *args, **kwargs)
            del self._trx_event[tsc.tid]
            del self._trx_mes_queue[tsc.tid]
            return res
        
        setattr(self, ttype, wrapper)
        self.transactions[ttype] = wrapper
    
    async def emit(self, event: str, *args, **kwargs):
        await self.context.send([event, args, kwargs])
    
    async def tsc(self, ttype: str, *args, **kwargs):
        return await self.transactions[ttype](*args, **kwargs)
    
    async def call(self, method: str, *args, **kwargs):
        cid = time_ns()
        self._resp_event[cid] = Event()
        
        await self.context.send(['call', method, cid, args, kwargs])
        
        await self._resp_event[cid].wait()
        del self._resp_event[cid]
        return self._resp_mes.pop(cid)
    
    def handle_client(
        self, 
        reader: StreamReader, 
        writer: StreamWriter,
    ):
        self.context = HakuClient.Context(
            writer, self.protocol
        )
        asyncio.ensure_future(self.event_loop(reader))
    
    async def event_loop(self, reader):
        while not self.context.is_closing():
            data = await self.protocol.read_obj(reader)
            if data is None:
                break
            
            match data:
                case ['tsc', tid, data]:
                    self._trx_mes_queue[tid].append(data)
                    self._trx_event[tid].set()
                
                case ['resp', cid, data]:
                    self._resp_mes[cid] = data
                    self._resp_event[cid].set()
                
                case [event, args, kwargs]:
                    if event in self.handlers:
                        await self.handlers[event](
                            self.context, *args, **kwargs
                        )
        
        await self.context.close()
