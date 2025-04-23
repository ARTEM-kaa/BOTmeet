from templates import texts
from model.models import User
from core.bot_instance import bot_instance


async def send_match_notification(tg_id: int, matched_user: User):
    message = await texts.match_notification(matched_user.tg_username)
    
    await bot_instance.send_message(
        chat_id=tg_id,
        text=message
    )
