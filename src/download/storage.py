import logging
import boto3
import requests
from io import BytesIO
from config import Config
from yandex_disk import get_download_url

logger = logging.getLogger(__name__)


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
