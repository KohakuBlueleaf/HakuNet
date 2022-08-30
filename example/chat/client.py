import asyncio

from hakunet.client import HakuClient


async def ainput(s: str = '') -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda s=s: input(s))


client = HakuClient('127.0.0.1', 10000)


@client.on_event('cli-mes')
async def mes(ctx: HakuClient.Context, user, mes):
    print(f'[User]{user}: {mes}')


@client.on_event('cli-login')
async def login_mes(ctx: HakuClient.Context, user):
    print(f'[System]: {user} login!')


@client.on_transaction('login')
async def login(ctx: HakuClient.TRXContext, user):
    await ctx.send(user)
    status, result = await ctx.read()
    
    if status:
        return True
    else:
        print(result)
        return False


async def main():
    async with client:
        while not (await client.tsc('login', user:=await ainput('user name:'))):
            pass
        
        print(f'Login as {user}!')
        
        while True:
            mes = await ainput()
            await client.emit('mes', mes)


asyncio.run(main())
