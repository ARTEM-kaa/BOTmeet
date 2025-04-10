from aiogram.types import Message
from templates import keyboards, texts


async def start(msg: Message) -> None:
    await msg.answer(
        await texts.start_message(), reply_markup=await keyboards.start_keyboard()
    )
