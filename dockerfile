# 基础镜像
FROM python:3.10

# 设置工作目录
WORKDIR /app

# 复制 Pipfile 和 Pipfile.lock 到容器中
COPY Pipfile Pipfile.lock /app/

# 安装依赖
RUN pip install pipenv && pipenv install --deploy --system

# 复制整个项目到容器中
COPY . /app

# 容器启动时执行的命令
CMD ["python", "src/main.py", "-c", "config.yaml"]