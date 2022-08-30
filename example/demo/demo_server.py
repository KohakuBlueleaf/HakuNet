from hakunet.server import HakuServer


server = HakuServer('127.0.0.1', 8000)


@server.on_event('mes')
async def mes(ctx: HakuServer.Context, mes):
    print(mes)
    await ctx.emit('reply', 'reply-test')


@server.on_call('ping')
async def pong():
    print('ping')
    return 'pong'


@server.on_transaction('fib')
async def fib(ctx: HakuServer.TRXContext):
    n = await ctx.read()
    a = 0
    b = 1
    for _ in range(n):
        a, b = b, a+b
        await ctx.send(a)


server.run()
