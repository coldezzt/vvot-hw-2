import json
import logging
import boto3
from config import Config

logger = logging.getLogger(__name__)


def send_task_message(
    config: Config,
    task_id: str,
    video_url: str,
) -> None:
    message = json.dumps(
        {
            "task_id": task_id,
            "video_url": video_url,
        },
        ensure_ascii=False,
    )

    client = boto3.client(
        service_name="sqs",
        endpoint_url="https://message-queue.api.cloud.yandex.net",
        region_name="ru-central1",
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key,
    )

    client.send_message(
        QueueUrl=config.queue_url,
        MessageBody=message,
        MessageAttributes={
            "Source": {
                "DataType": "String",
                "StringValue": "cloud-function",
            }
        },
    )

    logger.info(f"Message sent for task {task_id}")
