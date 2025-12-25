from main import handler

event = {
    "body": "lecture-title=Test+Lecture&yandex-link=https://yandex.ru/video",
    "isBase64Encoded": False,
}

response = handler(event, None)
print(response)
