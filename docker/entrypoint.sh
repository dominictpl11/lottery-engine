#!/bin/sh
set -e

# schema 的唯一真源是 Alembic 迁移，不是 create_all。容器启动时先对齐到 head，
# 保证「起容器」和「建表」不会变成两个需要人记住先后顺序的步骤。
#
# compose 里用 depends_on: service_healthy 等 MySQL 就绪，所以这里不再自己轮询。
echo "[entrypoint] applying migrations..."
alembic upgrade head

echo "[entrypoint] starting: $*"
exec "$@"
