from hakunet.server import HakuServer


server = HakuServer('127.0.0.1', 10000)
user_list: dict[str, HakuServer.Context] = {}
ctx_table: dict[HakuServer.Context, str] = {}


@server.on_event('mes')
async def mes(ctx: HakuServer.Context, mes):
    if ctx in ctx_table:
        await ctx.emit(
            'cli-mes', 
            ctx_table[ctx], mes,
            broadcast = True
        )


@server.on_transaction('login')
async def login(tctx: HakuServer.TRXContext):
    global user_list, ctx_table
    
    user = await tctx.read()
    if user in user_list:
        await tctx.send([False, 'User name already been used.'])
    else:
        user_list[user] = tctx.ctx
        ctx_table[tctx.ctx] = user
        await server.emit('cli-login', user)
        await tctx.send([True, 'OK'])


server.run()
