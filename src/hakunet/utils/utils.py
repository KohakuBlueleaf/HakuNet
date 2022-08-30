from typing import *

import struct
import socket
from asyncio import StreamReader, StreamWriter
from pickle import dumps, loads


def encode(x): return bytes(x, encoding='utf-8')
def decode(x): return bytes.decode(x)


def recv_msg(sock: socket.socket) -> Any:
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    return loads(recvall(sock, msglen))


def recvall(sock: socket.socket, n: int):
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data


def send_with_len(sock: socket.socket, data) -> None:
    data = dumps(data)
    data = struct.pack('>I', len(data)) + data
    sock.sendall(data)


def write_with_len(writer: StreamWriter, data):
    data = dumps(data)
    data = struct.pack('>I', len(data)) + data
    writer.write(data)


async def write_with_len_async(writer: StreamWriter, data):
    data = dumps(data)
    data = struct.pack('>I', len(data)) + data
    writer.write(data)
    await writer.drain()


async def read_msg(reader: StreamReader):
    raw_msglen = await readall(reader, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    data = await readall(reader, msglen)
    return loads(data)


async def readall(reader: StreamReader, n: int):
    data = b''
    while len(data) < n:
        packet = await reader.read(n - len(data))
        if not packet:
            return None
        data += packet
    return data