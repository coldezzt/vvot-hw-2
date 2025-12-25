import uuid
import datetime
import logging
import ydb
from config import Config

logger = logging.getLogger(__name__)


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
