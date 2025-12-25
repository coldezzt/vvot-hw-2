import uuid
import logging
import ydb
from config import Config

logger = logging.getLogger(__name__)


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
