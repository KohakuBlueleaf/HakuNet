import asyncio
from asyncio import ensure_future, sleep

from hakunet.client import HakuClient


client = HakuClient('127.0.0.1', 8000)


@client.on_event('reply')
async def reply(ctx: HakuClient.Context, mes):
    print(mes)


@client.on_transaction('fib')
async def fib(ctx: HakuClient.TRXContext, n):
    tid = ctx.tid.to_bytes(8, 'big').hex()[-6:]
    await ctx.send(n)
    
    for i in range(n):
        now = await ctx.read()
        print(f'tid: {tid}, fib_{i}: {now}')
        await sleep(0.001)


async def main():
    async with client:
        print('ping test:',await client.call('ping'))
        await client.emit(
            'mes', 
            'A test message from demo client.'
        )
        ensure_future(client.tsc('fib', 10))
        await sleep(0.04)
        ensure_future(client.tsc('fib', 10))


asyncio.run(main())
