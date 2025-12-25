from handler import handler

event = {
    "messages": [
        {
            "details": {
                "message": {
                    "body": '{"task_id":"00000000-0000-0000-0000-000000000000","video_url":"https://disk.yandex.ru/d/example"}'
                }
            }
        }
    ]
}

print(handler(event, None))