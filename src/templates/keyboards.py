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

async def preferences_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text=constants.MIN_AGE_BUTTON, callback_data=constants.MIN_AGE_CALL)],
        [InlineKeyboardButton(text=constants.MAX_AGE_BUTTON, callback_data=constants.MAX_AGE_CALL)],
        [InlineKeyboardButton(text=constants.MIN_RATING_BUTTON, callback_data=constants.MIN_RATING_CALL)],
        [InlineKeyboardButton(text=constants.MAX_RATING_BUTTON, callback_data=constants.MAX_RATING_CALL)],
        [InlineKeyboardButton(text=constants.RETURN_ACTION_BUTTON, callback_data=constants.RETURN_ACTION_CALL)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def edit_profile_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text=constants.EDIT_PHOTO_BUTTON, callback_data=constants.EDIT_PHOTO_CALL)],
        [InlineKeyboardButton(text=constants.EDIT_NAME_BUTTON, callback_data=constants.EDIT_NAME_CALL)],
        [InlineKeyboardButton(text=constants.EDIT_GENDER_BUTTON, callback_data=constants.EDIT_GENDER_CALL)],
        [InlineKeyboardButton(text=constants.EDIT_AGE_BUTTON, callback_data=constants.EDIT_AGE_CALL)],
        [InlineKeyboardButton(text=constants.EDIT_BIO_BUTTON, callback_data=constants.EDIT_BIO_CALL)],
        [InlineKeyboardButton(text=constants.EDIT_ALL_BUTTON, callback_data=constants.EDIT_ALL_CALL)],
        [InlineKeyboardButton(text=constants.EDIT_BACK_BUTTON, callback_data=constants.EDIT_BACK_CALL)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
