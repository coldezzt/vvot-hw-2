import json
import logging
import boto3
import requests
from config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_s3_client = None

def get_s3_client(config: Config):
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            's3',
            endpoint_url='https://storage.yandexcloud.net',
            region_name='ru-central1',
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
        )
    return _s3_client

def check_recognition_status(config: Config, operation_id: str) -> tuple[bool, dict]:
    logger.info(f"Checking status for operation ID: {operation_id}")
    headers = {"Authorization": f"Api-Key {config.ya_api_key}"}
    url = f"https://stt.api.cloud.yandex.net/stt/v3/getRecognition"
    
    try:
        response = requests.get(url, headers=headers, params={"operationId": operation_id})
        if response.status_code == 404:
            return False, response.json()
        # Последняя строка содержит результат
        return True, json.loads(response.text.splitlines()[-1])
    except Exception as e:
        logger.error(f"Failed to check recognition status: {str(e)}")
        raise

def save_recognition_result(config: Config, task_id: str, result_data: dict) -> str:
    s3 = get_s3_client(config)
    object_key = f"speech/{task_id}"
    s3.put_object(
        Bucket=config.s3_bucket_name,
        Key=object_key,
        Body=json.dumps(result_data, ensure_ascii=False),
        ContentType='application/json'
    )
    logger.info(f"Recognition result saved to {object_key}")
    return object_key

def send_message_to_queue(config: Config, message_body: str):
    logger.info(f"Sending message to queue: {config.summary_queue_url}")
    session = boto3.session.Session()
    sqs = session.client(
        service_name='sqs',
        endpoint_url='https://message-queue.api.cloud.yandex.net',
        region_name='ru-central1',
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key,
    )
    response = sqs.send_message(
        QueueUrl=config.summary_queue_url,
        MessageBody=message_body,
        MessageAttributes={'Source': {'StringValue': 'cloud-function', 'DataType': 'String'}}
    )
    logger.info(f"Message sent successfully. MessageId: {response.get('MessageId', 'Unknown')}")

def check_completed_tasks(config: Config):
    s3 = get_s3_client(config)
    response = s3.list_objects_v2(Bucket=config.s3_bucket_name, Prefix='speech-tasks/')
    if 'Contents' not in response:
        logger.info("No active tasks found")
        return

    for obj in response['Contents']:
        task_key = obj['Key']
        task_id = task_key.split('/')[-1]
        try:
            task_obj = s3.get_object(Bucket=config.s3_bucket_name, Key=task_key)
            task_info = json.loads(task_obj['Body'].read().decode('utf-8'))

            ok, resp = check_recognition_status(config, task_info['operation_id'])
            if ok:
                logger.info(f"Task {task_id} succeeded")
                result_json = json.loads(resp['result']['summarization']['results'][0]['response'])
                object_name = save_recognition_result(config, task_id, result_json)
                send_message_to_queue(config, json.dumps({"task_id": task_id, "object_name": object_name}))
                s3.delete_object(Bucket=config.s3_bucket_name, Key=task_key)
                logger.info(f"Task {task_id} processed and removed from active tasks")
            else:
                logger.info(f"Text not ready yet: {resp.get('error', {}).get('message', 'unknown')}")
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {str(e)}")
            continue

def handler(event, context):
    try:
        logger.info(f"Event: {json.dumps(event, ensure_ascii=False)}")
        config = Config()
        logger.info("Checking completed tasks")
        check_completed_tasks(config)
        return {'statusCode': 200}
    except Exception as e:
        logger.error(f"Error in handler: {str(e)}")
        return {'statusCode': 500, 'body': f'Error occurred: {str(e)}'}

if __name__ == "__main__":
    handler({'messages': []}, {})
