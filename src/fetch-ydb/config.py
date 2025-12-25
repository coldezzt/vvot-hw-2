import os
from dotenv import load_dotenv

load_dotenv(".env")

class Config:
    def __init__(self):
        self.ydb_endpoint = os.environ["YDB_ENDPOINT"]
        self.ydb_database = os.environ["YDB_DATABASE"]
        self.ydb_tasks_table_name = os.environ["YDB_TASKS_TABLE"]
