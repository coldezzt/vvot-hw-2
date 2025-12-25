import json
import logging
from dotenv import load_dotenv

from config import Config
from request import parse_form_request
from db import save_task
from queue import send_task_message

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    try:
        load_dotenv(".env")
        config = Config()

        logger.info(f"Incoming event: {json.dumps(event, ensure_ascii=False)}")

        data = parse_form_request(event)

        lecture_title = data.get("lecture-title", "")
        video_url = data.get("yandex-link", "")

        task_id = save_task(config, lecture_title, video_url)
        send_task_message(config, task_id, video_url)

        return {
            "statusCode": 302,
            "headers": {
                "Location": "/tasks",
            },
            "body": "Redirecting to /tasks",
            "isBase64Encoded": False,
        }

    except Exception as exc:
        logger.exception("Unhandled error")
        return {
            "statusCode": 500,
            "body": str(exc),
        }
