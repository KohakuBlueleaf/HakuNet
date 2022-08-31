# HakuNet
A simple socket framework for python

## install
```bash
git clone https://github.com/KohakuBlueleaf/HakuNet.git
cd HakuNet
# for windows, use python or py instead of python3
python3 -m pip install .
```

## Usage
A simple server example:
```py
from hakunet.server import HakuServer

server = HakuServer('127.0.0.1', 8000)

@server.on_call('ping')
async def pong():
    print('ping')
    return 'pong'

server.run()
```

And then setup client:
```py
import asyncio
from hakunet.client import HakuClient

client = HakuClient('127.0.0.1', 8000)

async def main():
    async with client:
        print(
            'ping test:',
            await client.call('ping')
        )

asyncio.run(main())
```

For more example, see `hakunet/example` folder.

---

## Todo
- [ ] more clear comments.
- [ ] add protocol module to manage more flexible protocol which now is using length header + pickle and it's not good.
- [ ] add ability to scale up.(difficult)
- [ ] more feature?
