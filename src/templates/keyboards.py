from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import templates.constants as constants

async def start_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=constants.START_BUTTON_TEXT, callback_data=constants.START_BUTTON_CALL)]
        ]
    )


async def gender_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=constants.MALE_BUTTON, callback_data=constants.MALE_CALL),
                InlineKeyboardButton(text=constants.FEMALE_BUTTON, callback_data=constants.FEMALE_CALL),
            ]
        ]
    )


async def main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text=constants.START_DATING_BUTTON, callback_data=constants.START_DATING_CALL)],
        [InlineKeyboardButton(text=constants.SET_PREFERENCES_BUTTON, callback_data=constants.SET_PREFERENCES_CALL)],
        [InlineKeyboardButton(text=constants.EDIT_PROFILE_BUTTON, callback_data=constants.EDIT_PROFILE_CALL)],
        [InlineKeyboardButton(text=constants.VIEW_LIKES_BUTTON, callback_data=constants.VIEW_LIKES_CALL)],
        [InlineKeyboardButton(text=constants.VIEW_RATING_BUTTON, callback_data=constants.VIEW_RATING_CALL)],
        [InlineKeyboardButton(text=constants.VIEW_COMMENTS_RECEIVED_BUTTON, callback_data=constants.VIEW_COMMENTS_RECEIVED_CALL)],
        [InlineKeyboardButton(text=constants.VIEW_COMMENTS_SENT_BUTTON, callback_data=constants.VIEW_COMMENTS_SENT_CALL)],
        [InlineKeyboardButton(text=constants.VIEW_MATCHES_BUTTON, callback_data=constants.VIEW_MATCHES_CALL)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
