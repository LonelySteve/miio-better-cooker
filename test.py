from datetime import datetime, timedelta


def pick_nearest_time_slots(time_slots):
    # 获取当前时间
    now = datetime.now()

    # 解析时间段
    time_slots_datetime = []
    for slot in time_slots:
        start_time_str, end_time_str = slot.split("-")
        # 获取今天对应的时间对象
        start_time = datetime.strptime(start_time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        end_time = datetime.strptime(end_time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        time_slots_datetime.append((start_time, end_time))

    # 找到符合就近未来原则的时间段
    for start_time, end_time in time_slots_datetime:
        if now <= end_time:
            # 如果当前时间在时间段内或还没有结束，返回当前时间段
            return [start_time, end_time]

    # 如果没有符合的时间段，返回明天的第一个时间段
    next_day = now + timedelta(days=1)
    first_start_time, first_end_time = time_slots_datetime[0]
    first_start_time = first_start_time.replace(
        year=next_day.year, month=next_day.month, day=next_day.day
    )
    first_end_time = first_end_time.replace(
        year=next_day.year, month=next_day.month, day=next_day.day
    )

    return [first_start_time, first_end_time]


# 测试用例
time_slots = ["08:00-08:30", "14:30-18:30", "17:30-19:00"]
print(pick_nearest_time_slots(time_slots))
