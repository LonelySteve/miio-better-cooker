def mask_password(password):
    # 如果密码长度小于等于 8，无法进行脱密处理
    if len(password) <= 8:
        return password
    # 将首尾 4 个字符之外的部分替换为星号
    return password[:4] + "*" * (len(password) - 8) + password[-4:]
