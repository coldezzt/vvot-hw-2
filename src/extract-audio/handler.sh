#!/usr/bin/env bash
set -Eeuo pipefail

require_env() {
  local missing=()

  for var in "$@"; do
    [[ -z "${!var:-}" ]] && missing+=("$var")
  done

  if (( ${#missing[@]} > 0 )); then
    echo "Missing env vars: ${missing[*]}" >&2
    exit 1
  fi
}

require_env \
  S3_BUCKET_NAME \
  SPEECH_QUEUE_URL \
  AWS_ACCESS_KEY_ID \
  AWS_SECRET_ACCESS_KEY

read_event() {
  jq -c '.messages[]'
}

extract_fields() {
  jq -r '
    .details.message.body
    | fromjson
    | [.task_id, .object_name]
    | @tsv
  '
}

send_queue_message() {
  local payload="$1"

  curl -sS \
    --request POST \
    --header 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode 'Action=SendMessage' \
    --data-urlencode "MessageBody=${payload}" \
    --data-urlencode "QueueUrl=${SPEECH_QUEUE_URL}" \
    --user "${AWS_ACCESS_KEY_ID}:${AWS_SECRET_ACCESS_KEY}" \
    --aws-sigv4 'aws:amz:ru-central1:sqs' \
    https://message-queue.api.cloud.yandex.net/ \
    >/dev/null
}

process_task() {
  local task_id="$1"
  local video_key="$2"

  local tmp_video="/tmp/${task_id}.video"
  local tmp_audio="/tmp/${task_id}.mp3"
  local audio_key="audio/${task_id}"

  echo "→ task=${task_id}" >&2

  yc storage s3api get-object \
    --bucket "${S3_BUCKET_NAME}" \
    --key "${video_key}" \
    "${tmp_video}" \
    >/dev/null

  ./ffmpeg \
    -loglevel error \
    -i "${tmp_video}" \
    -vn \
    -acodec libmp3lame \
    "${tmp_audio}"

  yc storage s3api put-object \
    --bucket "${S3_BUCKET_NAME}" \
    --key "${audio_key}" \
    --body "${tmp_audio}" \
    --content-type "audio/mpeg" \
    >/dev/null

  rm -f "${tmp_video}" "${tmp_audio}"

  local msg
  msg=$(jq -nc \
    --arg tid "${task_id}" \
    --arg obj "${audio_key}" \
    '{task_id: $tid, object_name: $obj}'
  )

  send_queue_message "${msg}"
}

main() {
  read_event |
  while read -r message; do
    extract_fields <<<"${message}" |
    while IFS=$'\t' read -r task_id video_key; do
      process_task "${task_id}" "${video_key}"
    done
  done

  echo '{"statusCode":200}'
}

main
