import requests
from urllib.parse import urlparse, quote


ALLOWED_DOMAINS = (
    "yadi.sk",
    "disk.yandex.ru",
    "disk.360.yandex.ru",
    "disk.yandex.com",
    "disk.360.yandex.com",
    "disk.yandex.by",
    "disk.360.yandex.by",
    "disk.yandex.kz",
    "disk.360.yandex.kz",
)


def is_public_video(url: str) -> bool:
    parsed = urlparse(url)

    if parsed.scheme != "https":
        return False

    if not any(parsed.netloc.endswith(domain) for domain in ALLOWED_DOMAINS):
        return False

    api_url = "https://cloud-api.yandex.net/v1/disk/public/resources"
    params = {"public_key": quote(url, safe="")}

    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return False

    return data.get("type") == "file" and data.get("mime_type", "").startswith("video/")


def get_download_url(public_url: str) -> str:
    api_url = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
    params = {"public_key": quote(public_url, safe="")}

    response = requests.get(api_url, params=params, timeout=10)
    response.raise_for_status()

    return response.json()["href"]
