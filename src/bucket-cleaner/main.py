import logging
import boto3
from botocore.exceptions import ClientError
from config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_s3_client = None

def get_s3_client(config: Config):
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            service_name='s3',
            endpoint_url="https://storage.yandexcloud.net",
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
        )
    return _s3_client

def delete_all_objects(config: Config):
    s3 = get_s3_client(config)
    bucket_name = config.s3_bucket_name
    logger.info(f"Starting deletion of all objects in bucket: {bucket_name}")
    
    total_deleted = 0
    continuation_token = None
    
    try:
        while True:
            list_kwargs = {'Bucket': bucket_name, 'MaxKeys': 1000}
            if continuation_token:
                list_kwargs['ContinuationToken'] = continuation_token

            response = s3.list_objects_v2(**list_kwargs)

            if 'Contents' not in response:
                logger.info("No objects found in the bucket.")
                break

            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]

            delete_response = s3.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': objects_to_delete}
            )

            deleted_count = len(delete_response.get('Deleted', []))
            total_deleted += deleted_count
            logger.info(f"Deleted {deleted_count} objects in this batch. Total deleted so far: {total_deleted}")

            if response.get('IsTruncated', False):
                continuation_token = response.get('NextContinuationToken')
            else:
                break

        logger.info(f"Successfully deleted all {total_deleted} objects from bucket {bucket_name}")
        return total_deleted

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            logger.error(f"Bucket {bucket_name} does not exist")
        else:
            logger.error(f"An error occurred: {e}")
        return 0

def handler(event, context):
    try:
        config = Config()
        total_deleted = delete_all_objects(config)
        return {
            'statusCode': 200,
            'body': f"Deleted {total_deleted} objects from bucket {config.s3_bucket_name}"
        }
    except Exception as e:
        logger.error(f"Error in handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': f"Error occurred: {str(e)}"
        }

if __name__ == "__main__":
    import os
    required_env_vars = ["S3_BUCKET_NAME", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    missing = [var for var in required_env_vars if var not in os.environ]
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        exit(1)
    handler({}, {})
