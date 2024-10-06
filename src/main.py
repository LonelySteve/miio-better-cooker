import argparse
import time
from datetime import datetime

from bark import pushMessage, setToken
from config import read_config
from cooker import PROFILES, MultiCooker, OperationMode
from logger import main_logger
from utils import mask_password

parser = argparse.ArgumentParser("my-smart-home")
parser.add_argument("-c", "--config-path", required=True)
args = parser.parse_args()

config_path = args.config_path
config = read_config(config_path)

main_logger.info(f"已成功加载配置，默认轮询周期为 {config.poll_interval} 秒")


print("=" * 70)
print(
    f"小饭煲IP：{config.cooker_config.ip}\t小饭煲TOKEN：{mask_password(config.cooker_config.token)}"
)
print(f"BARK TOKEN：{mask_password(config.push_config.token)}")
print("=" * 70)


setToken(config.push_config.token)


scheduled = False
last_akm_begin_time = None
last_mode: OperationMode = None
unplugged_check_push_count = 0

DEFAULT_COOKER = MultiCooker(
    ip=config.cooker_config.ip, token=config.cooker_config.token
)


def task():
    global scheduled, last_akm_begin_time, last_mode

    now = datetime.now()

    is_online = DEFAULT_COOKER.is_online()

    if is_online:
        mode = DEFAULT_COOKER.get_mode()

        if mode == OperationMode.AutoKeepWarm and (
            last_mode is None or last_mode == OperationMode.Running
        ):
            last_akm_begin_time = now
        if mode != OperationMode.AutoKeepWarm:
            last_akm_begin_time = None

        last_mode = mode
    else:
        last_akm_begin_time = None

    if config.cooker_config.unpluggedCheck:
        if (
            last_akm_begin_time
            and ((now - last_akm_begin_time).seconds / 60)
            > config.cooker_config.unpluggedMaxDuration
        ):
            main_logger.info(
                f"小饭煲处于保温模式且长时间未断电（{last_akm_begin_time.strftime('%H:%M')} - {now.strftime('%H:%M')}）"
            )
            if (
                unplugged_check_push_count
                < config.cooker_config.unpluggedMaxReminderCount
            ):
                pushMessage(
                    config.cooker_config.name,
                    "小饭煲处于保温模式且长时间未断电，请注意！",
                )
            if config.cooker_config.unpluggedAutoStopAkw:
                main_logger.info("自动停止小饭煲的保温模式")
                DEFAULT_COOKER.stop()
                pushMessage(
                    config.cooker_config.name,
                    "长时间处于保温模式且未断电，已自动停止小饭煲",
                )

    if scheduled == is_online:
        return
    if scheduled and not is_online:
        main_logger.info("小饭煲未上电，准备重新调度")
        scheduled = False
        return

    if mode != OperationMode.Waiting:
        main_logger.info("小饭煲不处于等待模式，视为已调度")
        scheduled = True
        return

    # 基本算法是，遍历 meal_profile_list，若当前时间恰好处于某一个就餐时间段内，则自动执行烹饪操作，否则将预约下一时间段的通常就餐时间开始烹饪
    for profile in config.cooker_config.meal_profile_list:
        earliest_time = profile.time.earliest_time.to_today_time()
        latest_time = profile.time.latest_time.to_today_time()
        usual_time = profile.time.usual_time.to_today_time()

        if earliest_time < now < latest_time:
            main_logger.info(
                f"当前处于 {earliest_time.strftime('%H:%M')} ~ {latest_time.strftime('%H:%M')} 就餐时间段内，小饭煲已上电，立即执行烹饪操作（{profile.type}）"
            )
            scheduled = True

            DEFAULT_COOKER.start(PROFILES[profile.type], akw=config.cooker_config.akw)
            pushMessage(
                config.cooker_config.name, f"小饭煲已自动开始烹饪（{profile.type}）"
            )
            break
        elif now < earliest_time:
            delta = usual_time - now
            minutes = delta.seconds // 60
            DEFAULT_COOKER.start(
                PROFILES[profile.type],
                schedule=minutes,
                akw=config.cooker_config.akw,
            )
            scheduled = True

            main_logger.info(
                f"小饭煲已上线，预定 {usual_time.strftime('%H:%M')}（{minutes}分钟后）烹饪完成（{profile.type}）并自动保温"
            )
            pushMessage(
                config.cooker_config.name,
                f"自动预定 {usual_time.strftime('%H:%M')}（{minutes}分钟后）烹饪完成（{profile.type}）并自动保温",
            )
            break


while True:
    task()
    time.sleep(config.poll_interval)
