from aiogram import F, Router
from aiogram.filters import CommandStart
import handlers.handlers as handlers
import templates.constants as constants
from states.states import RegistrationState, EditProfileState, PreferenceState, MeetingState

user_router = Router()

user_router.message.register(handlers.start, CommandStart())
user_router.callback_query.register(handlers.start_registration, F.data == constants.START_BUTTON_CALL)
user_router.message.register(handlers.get_full_name, RegistrationState.waiting_for_full_name)
user_router.message.register(handlers.get_age, RegistrationState.waiting_for_age)
user_router.callback_query.register(handlers.get_gender, RegistrationState.waiting_for_gender)
user_router.message.register(handlers.get_bio, RegistrationState.waiting_for_bio)
user_router.message.register(handlers.get_photo, RegistrationState.waiting_for_photo)
user_router.callback_query.register(handlers.preferences, F.data == constants.SET_PREFERENCES_CALL)
user_router.callback_query.register(handlers.show_likes_count, F.data == constants.VIEW_LIKES_CALL)
user_router.callback_query.register(handlers.show_rating, F.data == constants.VIEW_RATING_CALL)
user_router.callback_query.register(handlers.edit_profile, F.data == constants.EDIT_PROFILE_CALL)
user_router.callback_query.register(handlers.edit_photo, F.data == constants.EDIT_PHOTO_CALL)
user_router.callback_query.register(handlers.edit_full_name, F.data == constants.EDIT_NAME_CALL)
user_router.callback_query.register(handlers.edit_gender, F.data == constants.EDIT_GENDER_CALL)
user_router.callback_query.register(handlers.edit_age, F.data == constants.EDIT_AGE_CALL)
user_router.callback_query.register(handlers.edit_bio, F.data == constants.EDIT_BIO_CALL)
user_router.callback_query.register(handlers.edit_all, F.data == constants.EDIT_ALL_CALL)
user_router.callback_query.register(handlers.edit_back, F.data == constants.EDIT_BACK_CALL)
user_router.message.register(handlers.get_new_photo, EditProfileState.waiting_for_new_photo)
user_router.message.register(handlers.get_new_full_name, EditProfileState.waiting_for_new_name)
user_router.callback_query.register(handlers.get_new_gender, EditProfileState.waiting_for_new_gender)
user_router.message.register(handlers.get_new_age, EditProfileState.waiting_for_new_age)
user_router.message.register(handlers.get_new_bio, EditProfileState.waiting_for_new_bio)
user_router.callback_query.register(handlers.set_min_age, F.data == constants.MIN_AGE_CALL)
user_router.callback_query.register(handlers.set_max_age, F.data == constants.MAX_AGE_CALL)
user_router.callback_query.register(handlers.set_min_rating, F.data == constants.MIN_RATING_CALL)
user_router.callback_query.register(handlers.set_max_rating, F.data == constants.MAX_RATING_CALL)
user_router.callback_query.register(handlers.edit_back, F.data == constants.RETURN_ACTION_CALL)
user_router.message.register(handlers.save_min_age, PreferenceState.waiting_for_min_age)
user_router.message.register(handlers.save_max_age, PreferenceState.waiting_for_max_age)
user_router.message.register(handlers.save_min_rating, PreferenceState.waiting_for_min_rating)
user_router.message.register(handlers.save_max_rating, PreferenceState.waiting_for_max_rating)

user_router.callback_query.register(handlers.start_meeting, F.data == constants.START_DATING_CALL)
user_router.callback_query.register(handlers.like_profile, F.data == constants.LIKE_CALL)
user_router.callback_query.register(handlers.dislike_profile, F.data == constants.DISLIKE_CALL)
user_router.callback_query.register(handlers.comment_profile, F.data == constants.COMMENT_CALL)
user_router.callback_query.register(handlers.rate_profile, F.data.in_({
    constants.STAR_ONE_CALL,
    constants.STAR_TWO_CALL,
    constants.STAR_THREE_CALL,
    constants.STAR_FOUR_CALL,
    constants.STAR_FIVE_CALL,
}))
user_router.callback_query.register(handlers.back_to_profile, F.data == constants.BACK_TO_PROFILE_CALL)
user_router.message.register(handlers.get_comment, MeetingState.comment)
user_router.callback_query.register(handlers.edit_back, F.data == constants.BACK_TO_MENU_CALL)
