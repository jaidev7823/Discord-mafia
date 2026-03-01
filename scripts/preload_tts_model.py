import asyncio

from service.chatterbox_tts import load_global_model


async def main():
    await load_global_model()


if __name__ == "__main__":
    asyncio.run(main())
