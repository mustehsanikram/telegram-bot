from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(
        "Welcome. This bot manages your styling subscription and access to the private channel.\n\n"
        "Use /status to see where your subscription stands."
    )
