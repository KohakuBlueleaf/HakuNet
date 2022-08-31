from typing import Any
from asyncio import StreamReader, StreamWriter

from pickle import loads, dumps
from socket import socket


class BaseProtocol:
    def send_obj(
        self, 
        sender: socket,
        data: Any,
    ) -> None:
        raise NotImplementedError
    
    async def write_obj(
        self, 
        writer: StreamWriter,
        data: Any,
    ) -> None:
        raise NotImplementedError
    
    def recv_obj(
        self, 
        recevier: socket
    ) -> Any:
        raise NotImplementedError
    
    async def read_obj(
        self, 
        reader: StreamReader
    ) -> Any:
        raise NotImplementedError


class PickleProtocol(BaseProtocol):
    def encode(self, obj: Any) -> bytes:
        data = dumps(obj)
        data = len(data).to_bytes(8, 'big') + data
        return data
    
    async def write_obj(
        self,
        writer: StreamWriter,
        data: Any,
    ) -> None:
        encoded_data = self.encode(
            data
        )
        writer.write(encoded_data)
        await writer.drain()
    
    async def read_obj(
        self, 
        reader: StreamReader
    ) -> Any:
        length = int.from_bytes(
            await reader.read(8), 'big'
        )
        
        data = await reader.readexactly(length)
        if data != b'':
            return loads(data)
        else:
            return None