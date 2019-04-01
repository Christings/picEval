import json
import aiofiles


async def saveJson(content, filepath):
    async with aiofiles.open(filepath, 'w') as f:
        await f.write(json.dumps(content))


async def saveImg(content, filepath):
    async with aiofiles.open(filepath, 'wb+') as f:
        await f.write(content)

def saveJson1(content, filepath):
    with open(filepath, 'w') as f:
        f.write(json.dumps(content))

def saveImg1(content, filepath):
    with open(filepath, 'wb+') as f:
        f.write(content)

# def saveImg(content, filepath):
#     with aiofiles.open(filepath, 'w') as f:
#         f.write(content)
