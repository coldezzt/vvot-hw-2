import json
import logging
from dotenv import load_dotenv

from config import Config
from db import update_status
from storage import upload_video
from queue import send_to_extract_audio
from yandex_disk import is_public_video

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    load_dotenv(".env")
    config = Config()

    for message in event["messages"]:
        body = json.loads(message["details"]["message"]["body"])

        task_id = body["task_id"]
        video_url = body["video_url"]

        logger.info(f"Received task {task_id}")

        if not is_public_video(video_url):
            update_status(
                config,
                task_id,
                "Ошибка",
                "Ссылка не ведёт к публичному видео",
            )
            continue

        update_status(config, task_id, "В обработке", None)

        object_name = upload_video(config, task_id, video_url)
        send_to_extract_audio(config, task_id, object_name)

    return {"statusCode": 200}
