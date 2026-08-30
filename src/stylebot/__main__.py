import asyncio
import logging

from stylebot.bot import run_polling
from stylebot.config import get_settings


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(run_polling(get_settings()))


if __name__ == "__main__":
    run()
