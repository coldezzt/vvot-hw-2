import ydb
import uuid
import json
import boto3
import logging
import requests

from io import BytesIO
from config import Config
from dotenv import load_dotenv
from urllib.parse import urlparse, quote

logger = logging.getLogger(__name__)

ALLOWED_DOMAINS = (
    "yadi.sk",
    "disk.yandex.ru",
    "disk.360.yandex.ru",
    "disk.yandex.com",
    "disk.360.yandex.com",
    "disk.yandex.by",
    "disk.360.yandex.by",
    "disk.yandex.kz",
    "disk.360.yandex.kz",
)

def update_status(
    config: Config,
    task_id: str,
    status: str,
    description: str | None,
) -> None:
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
                UPDATE `{config.ydb_tasks_table}`
                SET status = $status, description = $description
                WHERE task_id = $task_id;
                """,
                {
                    "$task_id": (uuid.UUID(task_id), ydb.PrimitiveType.UUID),
                    "$status": (status, ydb.PrimitiveType.Utf8),
                    "$description": (
                        description,
                        ydb.OptionalType(ydb.PrimitiveType.Utf8),
                    ),
                },
            )

    logger.info(f"Status updated: {task_id} → {status}")

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
        QueueUrl=config.audio_queue_url,
        MessageBody=json.dumps(
            {
                "task_id": task_id,
                "object_name": object_name,
            },
            ensure_ascii=False,
        ),
    )

    logger.info(f"Sent extract-audio task for {task_id}")

def is_public_video(url: str) -> bool:
    parsed = urlparse(url)

    if parsed.scheme != "https":
        return False

    if not any(parsed.netloc.endswith(domain) for domain in ALLOWED_DOMAINS):
        return False

    api_url = "https://cloud-api.yandex.net/v1/disk/public/resources"
    params = {"public_key": quote(url, safe="")}

    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return False

    return data.get("type") == "file" and data.get("mime_type", "").startswith("video/")


def get_download_url(public_url: str) -> str:
    api_url = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
    params = {"public_key": quote(public_url, safe="")}

    response = requests.get(api_url, params=params, timeout=10)
    response.raise_for_status()

    return response.json()["href"]

def upload_video(
    config: Config,
    task_id: str,
    public_url: str,
) -> str:
    object_name = f"video/{task_id}"

    real_url = get_download_url(public_url)
    response = requests.get(real_url, timeout=30)
    response.raise_for_status()

    session = boto3.session.Session()
    s3 = session.client(
        service_name="s3",
        endpoint_url="https://storage.yandexcloud.net",
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key,
    )

    s3.upload_fileobj(
        BytesIO(response.content),
        config.s3_bucket,
        object_name,
        ExtraArgs={
            "ContentType": response.headers.get("content-type", "video/mp4")
        },
    )

    logger.info(f"Uploaded video to s3://{config.s3_bucket}/{object_name}")
    return object_name

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