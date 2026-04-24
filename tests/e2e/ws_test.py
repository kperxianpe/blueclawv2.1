import asyncio
import websockets
import json

async def test():
    uri = 'ws://localhost:8006/ws'
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            'type': 'task.start',
            'payload': {'user_input': 'Test input'},
            'timestamp': 1234567890,
            'message_id': 'test-001'
        }))
        
        for i in range(30):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(msg)
                t = data['type']
                p = json.dumps(data.get('payload', {}), ensure_ascii=False)[:200]
                print(f'[{i}] {t}: {p}')
                if t == 'thinking.node_created':
                    print('SUCCESS: thinking node created!')
                    break
                if t == 'error':
                    print('ERROR received')
                    break
            except asyncio.TimeoutError:
                print(f'[{i}] timeout')
                continue

asyncio.run(test())
