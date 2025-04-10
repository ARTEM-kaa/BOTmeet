from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import templates.constants as constants


async def start_keyboard() -> InlineKeyboardMarkup:
    Keyboard = [
        [
            InlineKeyboardButton(
                text=str(constants.START_BUTTON_TEXT), callback_data=constants.START_BUTTON_CALL
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=Keyboard)
