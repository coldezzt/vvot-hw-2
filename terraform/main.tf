# ===========================
# Terraform провайдер
# ===========================
terraform {
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = ">= 0.13"
    }
  }
  required_version = ">= 0.13"
}

provider "yandex" {
  zone = "ru-central1-d"
}

# ===========================
# YDB: база задач
# ===========================
resource "yandex_ydb_database_serverless" "tasks_db" {
  name      = "${var.prefix}-tasks-db"
  folder_id = var.folder_id
}

resource "yandex_ydb_table" "tasks_table" {
  path              = "${var.prefix}_dir/tasks_table"
  connection_string = yandex_ydb_database_serverless.tasks_db.ydb_full_endpoint

  column {
    name     = "created_at"
    type     = "Timestamp"
    not_null = true
  }
  column {
    name     = "task_id"
    type     = "UUID"
    not_null = true
  }
  column {
    name     = "lecture_title"
    type     = "Utf8"
    not_null = false
  }
  column {
    name     = "video_url"
    type     = "Utf8"
    not_null = false
  }
  column {
    name     = "status"
    type     = "Utf8"
    not_null = true
  }
  column {
    name     = "description"
    type     = "Utf8"
    not_null = false
  }

  primary_key = ["task_id"]
}

# ===========================
# Сервисный аккаунт и ключи
# ===========================
resource "yandex_iam_service_account" "main_sa" {
  folder_id = var.folder_id
  name      = "${var.prefix}-sa"
}

resource "yandex_resourcemanager_folder_iam_member" "sa_editor" {
  folder_id = var.folder_id
  role      = "editor"
  member    = "serviceAccount:${yandex_iam_service_account.main_sa.id}"
}

resource "yandex_iam_service_account_api_key" "sa_api_key" {
  service_account_id = yandex_iam_service_account.main_sa.id
}

resource "yandex_iam_service_account_static_access_key" "sa_static_key" {
  service_account_id = yandex_iam_service_account.main_sa.id
  description        = "static access key for storage and queues"
}

resource "yandex_resourcemanager_folder_iam_member" "sa_storage_admin" {
  folder_id = var.folder_id
  role      = "storage.admin"
  member    = "serviceAccount:${yandex_iam_service_account.main_sa.id}"
}

# ===========================
# Bucket для медиа и pdf
# ===========================
resource "yandex_storage_bucket" "media_bucket" {
  bucket     = "${var.prefix}-media-bucket"
  access_key = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
  depends_on = [yandex_resourcemanager_folder_iam_member.sa_storage_admin]

  lifecycle_rule {
    id      = "temp_files"
    enabled = true
    expiration { days = 1 }
  }
}

# ===========================
# Очереди сообщений
# ===========================
resource "yandex_message_queue" "dead_letter" {
  name       = "${var.prefix}-deadletter"
  access_key = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
}
data "yandex_message_queue" "dead_letter" {
  name       = yandex_message_queue.dead_letter.name
  access_key = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
}

resource "yandex_message_queue" "download_queue" {
  name                       = "${var.prefix}-download"
  visibility_timeout_seconds = 600
  receive_wait_time_seconds  = 20
  redrive_policy             = jsonencode({
    deadLetterTargetArn = yandex_message_queue.dead_letter.arn
    maxReceiveCount     = 3
  })
  access_key = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
}
data "yandex_message_queue" "download_queue" {
  name       = yandex_message_queue.download_queue.name
  access_key = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
}

resource "yandex_message_queue" "audio_queue" {
  name                       = "${var.prefix}-audio"
  visibility_timeout_seconds = 600
  receive_wait_time_seconds  = 20
  redrive_policy             = jsonencode({
    deadLetterTargetArn = yandex_message_queue.dead_letter.arn
    maxReceiveCount     = 3
  })
  access_key = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
}
data "yandex_message_queue" "audio_queue" {
  name       = yandex_message_queue.audio_queue.name
  access_key = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
}

resource "yandex_message_queue" "speech_queue" {
  name                       = "${var.prefix}-speech"
  visibility_timeout_seconds = 600
  receive_wait_time_seconds  = 20
  redrive_policy             = jsonencode({
    deadLetterTargetArn = yandex_message_queue.dead_letter.arn
    maxReceiveCount     = 3
  })
  access_key = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
}
data "yandex_message_queue" "speech_queue" {
  name       = yandex_message_queue.speech_queue.name
  access_key = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
}

resource "yandex_message_queue" "summary_queue" {
  name       = "${var.prefix}-summary"
  access_key = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
}
data "yandex_message_queue" "summary_queue" {
  name       = yandex_message_queue.summary_queue.name
  access_key = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
}

# ===========================
# Функции
# ===========================
# 1. task_ingestor
data "archive_file" "task_ingestor_zip" {
  type        = "zip"
  output_path = "task_ingestor.zip"
  source_dir  = "../src/form-receiver"
  excludes    = [".env", "*.pyc", "__pycache__"]
}

resource "yandex_function" "task_ingestor" {
  name               = "${var.prefix}-task-ingestor"
  description        = "Принимает форму, создаёт задачу в YDB, шлёт сообщение в очередь download"
  user_hash          = data.archive_file.task_ingestor_zip.output_sha256
  runtime            = "python312"
  entrypoint         = "main.handler"
  memory             = "128"
  execution_timeout  = "60"
  folder_id          = var.folder_id
  service_account_id = yandex_iam_service_account.main_sa.id
  content { zip_filename = data.archive_file.task_ingestor_zip.output_path }

  environment = {
    YDB_ENDPOINT          = "grpcs://${yandex_ydb_database_serverless.tasks_db.ydb_api_endpoint}"
    YDB_DATABASE          = yandex_ydb_database_serverless.tasks_db.database_path
    YDB_TASKS_TABLE       = yandex_ydb_table.tasks_table.path
    AWS_ACCESS_KEY_ID     = yandex_iam_service_account_static_access_key.sa_static_key.access_key
    AWS_SECRET_ACCESS_KEY = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
    DOWNLOAD_QUEUE_URL    = data.yandex_message_queue.download_queue.url
  }
}

# 2. media_fetcher
data "archive_file" "media_fetcher_zip" {
  type        = "zip"
  output_path = "media_fetcher.zip"
  source_dir  = "../src/download"
  excludes    = [".env", "*.pyc", "__pycache__"]
}

resource "yandex_function" "media_fetcher" {
  name               = "${var.prefix}-media-fetcher"
  description        = "Берет сообщение с download queue, сохраняет video/* в bucket, шлет имя объекта в audio queue"
  user_hash          = data.archive_file.media_fetcher_zip.output_sha256
  runtime            = "python312"
  entrypoint         = "handler.main" # main.handler -> handler.main
  memory             = "1024"
  execution_timeout  = "120"
  folder_id          = var.folder_id
  service_account_id = yandex_iam_service_account.main_sa.id
  content { zip_filename = data.archive_file.media_fetcher_zip.output_path }

  environment = {
    YDB_ENDPOINT          = "grpcs://${yandex_ydb_database_serverless.tasks_db.ydb_api_endpoint}"
    YDB_DATABASE          = yandex_ydb_database_serverless.tasks_db.database_path
    YDB_TASKS_TABLE       = yandex_ydb_table.tasks_table.path
    
    S3_BUCKET_NAME        = yandex_storage_bucket.media_bucket.bucket
    AUDIO_QUEUE_URL       = data.yandex_message_queue.audio_queue.url

    AWS_ACCESS_KEY_ID     = yandex_iam_service_account_static_access_key.sa_static_key.access_key
    AWS_SECRET_ACCESS_KEY = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
  }
}

# 3. audio_extractor
data "archive_file" "audio_extractor_zip" {
  type        = "zip"
  output_path = "audio_extractor.zip"
  source_dir  = "../src/extract-audio"
}

resource "yandex_storage_object" "audio_extractor_package" {
  bucket = yandex_storage_bucket.media_bucket.bucket
  key    = "audio_extractor.zip"
  source = data.archive_file.audio_extractor_zip.output_path
}

resource "yandex_function" "audio_extractor" {
  name               = "${var.prefix}-audio-extractor"
  description        = "Извлекает аудио, сохраняет в bucket, отправляет сообщение в speech queue"
  user_hash          = data.archive_file.audio_extractor_zip.output_sha256
  runtime            = "bash-2204"
  entrypoint         = "handler.sh"
  memory             = "128"
  execution_timeout  = "120"
  folder_id          = var.folder_id
  service_account_id = yandex_iam_service_account.main_sa.id
  package {
    bucket_name = yandex_storage_bucket.media_bucket.bucket
    object_name = yandex_storage_object.audio_extractor_package.key
  }
  environment = {    
    S3_BUCKET_NAME        = yandex_storage_bucket.media_bucket.bucket
    SPEECH_QUEUE_URL      = data.yandex_message_queue.speech_queue.url
    
    AWS_ACCESS_KEY_ID     = yandex_iam_service_account_static_access_key.sa_static_key.access_key
    AWS_SECRET_ACCESS_KEY = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
  }
}

# 4. speech_analyzer
data "archive_file" "speech_analyzer_zip" {
  type        = "zip"
  output_path = "speech_analyzer.zip"
  source_dir  = "../src/recognize-speech"
}

resource "yandex_function" "speech_analyzer" {
  name               = "${var.prefix}-speech-analyzer"
  description        = "Отправляет аудио на распознавание, сохраняет промежуточно в bucket/speech-tasks"
  user_hash          = data.archive_file.speech_analyzer_zip.output_sha256
  runtime            = "python312"
  entrypoint         = "main.handler"
  memory             = "1024"
  execution_timeout  = "120"
  folder_id          = var.folder_id
  service_account_id = yandex_iam_service_account.main_sa.id
  content { zip_filename = data.archive_file.speech_analyzer_zip.output_path }

  environment = {
    S3_BUCKET_NAME        = yandex_storage_bucket.media_bucket.bucket
    YA_API_KEY            = yandex_iam_service_account_api_key.sa_api_key.secret_key
    FOLDER_ID             = var.folder_id

    AWS_ACCESS_KEY_ID     = yandex_iam_service_account_static_access_key.sa_static_key.access_key
    AWS_SECRET_ACCESS_KEY = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
  }
}

# 5. speech_monitor
data "archive_file" "speech_monitor_zip" {
  type        = "zip"
  output_path = "speech_monitor.zip"
  source_dir  = "../src/recognize-speech-cron"
}

resource "yandex_function" "speech_monitor" {
  name                   = "${var.prefix}-speech-monitor"
  description            = "Проверяет все speech-tasks/*, сохраняет результат в speech/* и шлет в summary queue"
  user_hash              = data.archive_file.speech_monitor_zip.output_sha256
  runtime                = "python312"
  entrypoint             = "main.handler"
  memory                 = "256"
  execution_timeout      = "60"
  folder_id              = var.folder_id
  service_account_id     = yandex_iam_service_account.main_sa.id
  content { zip_filename = data.archive_file.speech_monitor_zip.output_path }

  environment = {
    YA_API_KEY            = yandex_iam_service_account_api_key.sa_api_key.secret_key

    S3_BUCKET_NAME        = yandex_storage_bucket.media_bucket.bucket
    SUMMARY_QUEUE_URL     = data.yandex_message_queue.summary_queue.url

    AWS_ACCESS_KEY_ID     = yandex_iam_service_account_static_access_key.sa_static_key.access_key
    AWS_SECRET_ACCESS_KEY = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
  }
}

# 6. pdf_generator
data "archive_file" "pdf_generator_zip" {
  type        = "zip"
  output_path = "pdf_generator.zip"
  source_dir  = "../src/summary"
}

resource "yandex_function" "pdf_generator" {
  name               = "${var.prefix}-pdf-generator"
  description        = "Создает HTML и PDF из распознанного текста, сохраняет в bucket/pdf"
  user_hash          = data.archive_file.pdf_generator_zip.output_sha256
  runtime            = "python312"
  entrypoint         = "main.handler"
  memory             = "1024"
  execution_timeout  = "120"
  folder_id          = var.folder_id
  service_account_id = yandex_iam_service_account.main_sa.id
  content { zip_filename = data.archive_file.pdf_generator_zip.output_path }

  environment = {
    YA_API_KEY            = yandex_iam_service_account_api_key.sa_api_key.secret_key

    YDB_ENDPOINT          = "grpcs://${yandex_ydb_database_serverless.tasks_db.ydb_api_endpoint}"
    YDB_DATABASE          = yandex_ydb_database_serverless.tasks_db.database_path
    YDB_TASKS_TABLE       = yandex_ydb_table.tasks_table.path

    FOLDER_ID             = var.folder_id
    S3_BUCKET_NAME        = yandex_storage_bucket.media_bucket.bucket

    AWS_ACCESS_KEY_ID     = yandex_iam_service_account_static_access_key.sa_static_key.access_key
    AWS_SECRET_ACCESS_KEY = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
  }
}

# 7. task_fetcher
data "archive_file" "task_fetcher_zip" {
  type        = "zip"
  output_path = "task_fetcher.zip"
  source_dir  = "../src/fetch-ydb"
}

resource "yandex_function" "task_fetcher" {
  name               = "${var.prefix}-task-fetcher"
  description        = "Возвращает все задачи из YDB"
  user_hash          = data.archive_file.task_fetcher_zip.output_sha256
  runtime            = "python312"
  entrypoint         = "main.handler"
  memory             = "256"
  execution_timeout  = "60"
  folder_id          = var.folder_id
  service_account_id = yandex_iam_service_account.main_sa.id
  content { zip_filename = data.archive_file.task_fetcher_zip.output_path }

  environment = {
    YDB_ENDPOINT        = "grpcs://${yandex_ydb_database_serverless.tasks_db.ydb_api_endpoint}"
    YDB_DATABASE        = yandex_ydb_database_serverless.tasks_db.database_path
    YDB_TASKS_TABLE     = yandex_ydb_table.tasks_table.path
  }
}

# ===========================
# API Gateway (html + fetch)
# ===========================
resource "yandex_storage_object" "form_page" {
  bucket       = yandex_storage_bucket.media_bucket.bucket
  key          = "form.html"
  source       = "../src/html/form.html"
  content_type = "text/html"
}

resource "yandex_storage_object" "tasks_page" {
  bucket       = yandex_storage_bucket.media_bucket.bucket
  key          = "tasks.html"
  source       = "../src/html/tasks.html"
  content_type = "text/html"
}

resource "yandex_api_gateway" "tasks_gateway" {
  name      = "${var.prefix}-gateway"
  folder_id = var.folder_id

  spec = templatefile("./gateway_spec.yaml.tpl", {
    api_name               = "${var.prefix}-api"
    bucket_name            = yandex_storage_bucket.media_bucket.bucket
    form_key               = yandex_storage_object.form_page.key
    tasks_key              = yandex_storage_object.tasks_page.key
    service_account_id     = yandex_iam_service_account.main_sa.id
    task_fetcher_function  = yandex_function.task_fetcher.id
    task_ingestor_function = yandex_function.task_ingestor.id
  })
}

output "gateway_url" {
  value       = yandex_api_gateway.tasks_gateway.domain
  description = "URL API Gateway"
}
