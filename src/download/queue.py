import json
import logging
import boto3
from config import Config

logger = logging.getLogger(__name__)


def send_to_extract_audio(
    config: Config,
    task_id: str,
    object_name: str,
) -> None:
    client = boto3.client(
        service_name="sqs",
        endpoint_url="https://message-queue.api.cloud.yandex.net",
        region_name="ru-central1",
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key,
    )

    client.send_message(
        QueueUrl=config.extract_audio_queue_url,
        MessageBody=json.dumps(
            {
                "task_id": task_id,
                "object_name": object_name,
            },
            ensure_ascii=False,
        ),
    )

    logger.info(f"Sent extract-audio task for {task_id}")
