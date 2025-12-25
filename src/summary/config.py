import os
from dotenv import load_dotenv

load_dotenv(".env")

class Config:
    def __init__(self):
        self.ya_api_key = os.environ["YA_API_KEY"]

        self.ydb_endpoint = os.environ["YDB_ENDPOINT"]
        self.ydb_database = os.environ["YDB_DATABASE"]
        self.ydb_tasks_table_name = os.environ["YDB_TASKS_TABLE"]

        self.folder_id = os.environ["FOLDER_ID"]
        self.s3_bucket_name = os.environ["S3_BUCKET_NAME"]

        self.aws_access_key_id = os.environ["AWS_ACCESS_KEY_ID"]
        self.aws_secret_access_key = os.environ["AWS_SECRET_ACCESS_KEY"]
