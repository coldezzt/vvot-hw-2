# vvot-hw-2

## extract-audio

Cloud Function для извлечения аудиодорожки из видео.

### Зависимости
- статически собранный `ffmpeg` рядом с `handler.sh`
- доступ к S3 и Message Queue

### Поток
S3(video) → ffmpeg → S3(audio) → SQS
