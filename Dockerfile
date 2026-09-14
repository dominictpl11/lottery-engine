# API 镜像（REQUIREMENTS.md 8.6）。
#
# 用 slim 而不是 alpine：alpine 的 musl libc 会让部分带 C 扩展的轮子
# （这里是 cryptography）退化成源码编译，构建慢且容易出问题。

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先装依赖再拷代码：改代码不会让依赖层失效，重建快很多。
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini ./
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# 不用 root 跑应用。
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
