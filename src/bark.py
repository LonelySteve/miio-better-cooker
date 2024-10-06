import requests

from logger import bark_logger

TOKEN = ""


def setToken(token: str):
    global TOKEN
    TOKEN = token


def pushMessage(title: str, message: str):
    if not TOKEN:
        bark_logger.warning(f"bark token 未设置，无法推送消息：{message}")
        return

    try:
        res = requests.get(f"https://api.day.app/{TOKEN}/{title}/{message}")

        data = res.json()
        success = data and data["code"]

        if success:
            bark_logger.info(f"消息已推送：{message}")
        else:
            bark_logger.error(
                f"消息推送失败[{data['code'] if data else -1}]：{message}"
            )

        return success
    except Exception as ex:
        bark_logger.error("消息推送失败", ex)
        return False
