# Lottery Engine — Python 版（主线实现）

营销抽奖服务。本目录是项目的**唯一在维护的实现**；Java 版已冻结为 Legacy。

- 规划与阶段排期：[`docs/PROJECT_PLAN.md`](../docs/PROJECT_PLAN.md)
- 需求规格与验收标准：[`REQUIREMENTS.md`](REQUIREMENTS.md)
- 索引验证结果：[`docs/db-explain.md`](../docs/db-explain.md)

## 环境

- Python 3.11+
- Docker（用于起 MySQL 与 Redis）
- 数据库：MySQL 8.4
- 默认端口：`8000`

## 启动

```bash
cd lottery_python

# 1. 依赖服务（MySQL 8.4 + Redis 7）
cp .env.example .env          # 按需修改，.env 不提交
docker compose up -d

# 2. Python 环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # 非 PowerShell 用对应的激活命令
python -m pip install -r requirements.txt

# 3. 建表（schema 的唯一真源是 migration，不用 create_all）
python -m alembic upgrade head

# 4. 起服务
python -m uvicorn app.main:app --reload --port 8000
```

访问：

- 健康检查：`http://127.0.0.1:8000/api/health`
- Swagger：`http://127.0.0.1:8000/docs`

> MySQL 映射在宿主机 **3307**，避免和本机已有的 MySQL 实例抢 3306。

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/activities` | 创建活动（201） |
| `GET` | `/api/activities/{activity_id}` | 查询活动配置 |
| `POST` | `/api/activities/{activity_id}/awards` | 配置奖品（201） |
| `POST` | `/api/lottery/draw` | 执行抽奖 |

抽奖请求与响应示例见 [`REQUIREMENTS.md` §6](REQUIREMENTS.md)。

两点契约上的注意：

- 时间入参**必须带时区偏移**（如 `2026-09-14T18:00:00+08:00`）。不带偏移的 naive 值返回 422，
  不会被猜成 UTC。
- `success` 表示**流程是否正常完成**，不表示是否中奖。中奖/未中奖都是 `true`；
  业务拒绝才是 `false`，并带固定分类的 `reject_reason`。

## 当前状态：Phase 1 完成

**已具备**：

| | |
| --- | --- |
| 存储 | MySQL 8.4，Alembic 迁移可从空库复现完整结构 |
| Schema | 唯一约束、外键、CHECK 约束、按查询设计的索引（3 条主查询 EXPLAIN 全部命中） |
| 事务 | 奖品库存扣减与订单写入在同一事务；失败则回滚并归还活动库存与当日配额 |
| 时区 | 库内 naive UTC，应用内 aware UTC，边界显式转换 |
| 业务 | 活动/奖品配置、加权抽奖、订单落库、频率限流、每日参与次数 |
| 运行 | `docker compose up -d` 起 MySQL + Redis |

**仍然不正确 / 尚未实现**：

| | 现状 |
| --- | --- |
| 库存扣减（D1） | 仍是 read-then-write，**并发下会超卖**。Phase 2 用 Redis Lua 原子扣减替换 |
| 限流与每日次数（D5） | 仍是**进程内**实现，多 worker 下各算各的，且进程重启即失忆。Phase 2 换成 Redis |
| Redis（D8） | 容器已起，但应用**尚未接入**，`enable_redis` 仍是占位配置 |
| 幂等（FR-5） | `draw_order.request_id` 的 UNIQUE 约束已就位，但值目前由服务端生成，**没有真正的幂等语义**。Phase 2 改为客户端提供 + Redis 检查 |

**完全没有**：pytest、Locust 压测、API 容器化。

缺陷清单见 [`REQUIREMENTS.md` §9.1](REQUIREMENTS.md)，下一步是 Phase 2（Redis 并发控制）。

## 约定

`.venv/`、`.env`、本地数据库文件和 Python 缓存都不提交。密码只放 `.env`，
`.env.example` 里只放占位值。
