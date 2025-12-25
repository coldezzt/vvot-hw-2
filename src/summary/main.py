import json
import logging
import boto3
import io
from weasyprint import HTML
from dotenv import load_dotenv
from config import Config
import ydb
import uuid
from yandex_cloud_ml_sdk import YCloudML

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_lecture_name(config: Config, task_id: str) -> str:
    driver_config = ydb.DriverConfig(
        config.ydb_endpoint,
        config.ydb_database,
        credentials=ydb.credentials_from_env_variables(),
        root_certificates=ydb.load_ydb_root_certificate(),
    )
    logger.info(f"Getting lecture name for task_id {task_id}")
    with ydb.Driver(driver_config) as driver:
        driver.wait(timeout=5)
        with ydb.QuerySessionPool(driver) as pool:
            id = uuid.UUID(task_id)
            result_sets = pool.execute_with_retries(
                f"SELECT lecture_title FROM `{config.ydb_tasks_table_name}` WHERE task_id = $taskId",
                {"$taskId": (id, ydb.PrimitiveType.UUID)}
            )
            return result_sets[0].rows[0].lecture_title

def change_status_in_db(config: Config, task_id: str, status: str, description: str | None):
    driver_config = ydb.DriverConfig(
        config.ydb_endpoint,
        config.ydb_database,
        credentials=ydb.credentials_from_env_variables(),
        root_certificates=ydb.load_ydb_root_certificate(),
    )
    logger.info(f"Updating status {status} for task_id {task_id}")
    with ydb.Driver(driver_config) as driver:
        driver.wait(timeout=5)
        with ydb.QuerySessionPool(driver) as pool:
            id = uuid.UUID(task_id)
            pool.execute_with_retries(
                f"UPDATE `{config.ydb_tasks_table_name}` SET status=$status, description=$description WHERE task_id=$taskId",
                {
                    "$taskId": (id, ydb.PrimitiveType.UUID),
                    "$status": (status, ydb.PrimitiveType.Utf8),
                    "$description": (description, ydb.OptionalType(ydb.PrimitiveType.Utf8))
                }
            )

def get_speech_summary_from_s3(config: Config, object_name: str) -> str:
    s3 = boto3.client(
        's3',
        endpoint_url='https://storage.yandexcloud.net',
        region_name='ru-central1',
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key,
    )
    resp = s3.get_object(Bucket=config.s3_bucket_name, Key=object_name)
    return resp["Body"].read().decode("utf-8")

def get_ai_html_summary(config: Config, lecture_name: str, speech_summary: str) -> str:
    instruction = (
        f"Тебе даётся ТЕКСТ конспекта лекции в JSON. Сделай из него HTML с <h1>{lecture_name}</h1> в начале body. "
        "Ответ только в одной строке, без новых строк и табов. ТЕКСТ:"
    )
    sdk = YCloudML(folder_id=config.folder_id, auth=config.ya_api_key)
    model = sdk.models.completions("yandexgpt-lite", model_version="rc").configure(temperature=0.2)
    messages = [{"role": "system", "text": instruction}, {"role": "user", "text": speech_summary}]
    result = model.run(messages)
    return result.alternatives[0].text

def generate_s3_pdf_from_html(config: Config, html_str: str, task_id: str, lecture_name: str) -> str:
    pdf_buffer = io.BytesIO()
    HTML(string=html_str).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    object_name = f"pdf/{task_id}/{lecture_name}.pdf"
    s3_client = boto3.client(
        's3',
        endpoint_url='https://storage.yandexcloud.net',
        region_name='ru-central1',
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key,
    )
    s3_client.upload_fileobj(pdf_buffer, config.s3_bucket_name, object_name, ExtraArgs={'ContentType': 'application/pdf'})
    pdf_buffer.close()
    logger.info(f"PDF uploaded as {object_name}")
    return object_name

def handler(event, context):
    try:
        logger.info(f"Event: {json.dumps(event, ensure_ascii=False)}")
        load_dotenv(".env")
        config = Config()
        for message in event["messages"]:
            body = json.loads(message['details']['message']['body'])
            task_id = body['task_id']
            object_name = body['object_name']

            speech_summary = get_speech_summary_from_s3(config, object_name)
            lecture_name = get_lecture_name(config, task_id)
            html_summary = get_ai_html_summary(config, lecture_name, speech_summary)
            pdf_object_name = generate_s3_pdf_from_html(config, html_summary, task_id, lecture_name)
            change_status_in_db(config, task_id, "Успешно завершено", pdf_object_name)

        return {'statusCode': 200}

    except Exception as e:
        logger.error(f"Error in handler: {str(e)}")
        return {'statusCode': 500, 'body': f'Error occurred: {str(e)}'}

if __name__ == "__main__":
    handler({"messages": []}, {})
