
import ydb
import json
import uuid
import boto3
import base64
import datetime
import logging

from dotenv import load_dotenv
from config import Config
from urllib.parse import parse_qs

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def parse_form_request(event: dict) -> dict:
    body = event.get("body", "")
    is_base64 = event.get("isBase64Encoded", False)

    if is_base64 and body:
        body = base64.b64decode(body).decode("utf-8")

    try:
        parsed = parse_qs(body)
        return {key: values[0] for key, values in parsed.items()}
    except Exception as exc:
        logger.error(f"Failed to parse request body: {exc}")
        return {}

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

def save_task(
    config: Config,
    lecture_title: str,
    video_url: str,
) -> str:
    task_id = uuid.uuid4()
    created_at = datetime.datetime.now(datetime.timezone.utc)

    driver_config = ydb.DriverConfig(
        config.ydb_endpoint,
        config.ydb_database,
        credentials=ydb.credentials_from_env_variables(),
        root_certificates=ydb.load_ydb_root_certificate(),
    )

    with ydb.Driver(driver_config) as driver:
        driver.wait(timeout=5)

        with ydb.QuerySessionPool(driver) as pool:
            pool.execute_with_retries(
                f"""
                DECLARE $task_id AS Uuid;
                DECLARE $created_at AS Timestamp;
                DECLARE $lecture_title AS Utf8;
                DECLARE $video_url AS Utf8;

                UPSERT INTO `{config.ydb_tasks_table}` (
                    task_id,
                    created_at,
                    lecture_title,
                    video_url,
                    status,
                    description
                )
                VALUES (
                    $task_id,
                    $created_at,
                    $lecture_title,
                    $video_url,
                    'В очереди',
                    NULL
                );
                """,
                {
                    "$task_id": (task_id, ydb.PrimitiveType.UUID),
                    "$created_at": (created_at, ydb.PrimitiveType.Timestamp),
                    "$lecture_title": (lecture_title, ydb.PrimitiveType.Utf8),
                    "$video_url": (video_url, ydb.PrimitiveType.Utf8),
                },
            )

    logger.info(f"Task saved: {task_id}")
    return str(task_id)

def handler(event, context):
    try:
        load_dotenv(".env")
        config = Config()

        logger.info(f"Incoming event: {json.dumps(event, ensure_ascii=False)}")

        data = parse_form_request(event)

        lecture_title = data.get("lecture", "")
        video_url = data.get("video_url", "")

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
