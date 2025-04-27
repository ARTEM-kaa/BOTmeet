from typing import Any, Dict

from consumer.handlers.check_user_in_db import check_registration
from consumer.handlers.registration import create_user_profile
from consumer.handlers.update_preferences import update_preferences_handler
from consumer.handlers.photo_processing import process_photo_update
from consumer.handlers.meeting import process_get_next_profile
from consumer.handlers.likes import process_like
from consumer.handlers.profile_updates import process_profile_update
import logging
logger = logging.getLogger(__name__)


async def event_distribution(body: Dict[str, Any]) -> None:
    logger.info(f"Received message: {body}")
    try:
        match body['action']:
            case 'check_user_in_db':
                await check_registration(body)
            case 'create_user_profile':
                await create_user_profile(body)
            case 'update_preferences':
                await update_preferences_handler(body)
            case 'update_photo':
                await process_photo_update(body)
            case 'get_next_profile':
                logger.info("Processing get_next_profile request")
                await process_get_next_profile(body)
            case 'process_like':
                await process_like(body)
            case 'process_dislike':
                await process_like({**body, 'is_like': False})
            case 'update_profile_field':
                await process_profile_update(body)
    except Exception as e:
        logger.exception(f"Error processing message: {e}")