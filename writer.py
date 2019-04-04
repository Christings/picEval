import json
import aiofiles


async def saveJson(content, filepath):
    async with aiofiles.open(filepath, 'w') as f:
        await f.write(json.dumps(content))


async def saveImg(content, filepath):
    async with aiofiles.open(filepath, 'wb+') as f:
        await f.write(content)

