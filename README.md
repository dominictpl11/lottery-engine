# Lottery Engine

并发安全的营销抽奖服务。

> 这里的 "lottery" 指**营销抽奖**（运营活动里的抽奖/转盘），不是彩票号码预测。

用一个范围受控的业务系统，证明数据库设计、缓存、并发正确性、幂等、自动化测试与性能验证
这几项工程能力——每一条技术主张都要有可复现的测试或 benchmark 支撑，而不是只在 README 里
写一句"支持高并发"。

技术栈：Python 3.11 · FastAPI · SQLAlchemy 2 · MySQL 8.4 · Alembic · Redis · Docker Compose

## 快速开始

```bash
cp .env.example .env          # 按需修改；.env 含密码，不提交
docker compose up -d          # MySQL 8.4 + Redis 7

python -m venv .venv
.\.venv\Scripts\Activate.ps1  # 非 PowerShell 用对应的激活命令
python -m pip install -r requirements.txt

python -m alembic upgrade head            # 建表：schema 的唯一真源是 migration
python -m uvicorn app.main:app --reload --port 8000
```

- 健康检查：`http://127.0.0.1:8000/api/health`
- Swagger：`http://127.0.0.1:8000/docs`

> MySQL 映射在宿主机 **3307**，避开本机可能已有的 MySQL 实例。

## 测试

```bash
pip install -r requirements.txt -r requirements-dev.txt
docker compose up -d
pytest                    # 全量
pytest -m concurrency     # 只跑并发用例（较慢）
```

测试跑在独立的 `lottery_test` 库与 Redis `db 1` 上，与开发数据完全隔离；
`conftest.py` 里有断言保证跑错目标时直接失败，而不是清空开发库。

| 层 | 用例 | 覆盖 |
| --- | --- | --- |
| `tests/unit/` | 16 | 抽奖算法（含 10 万次分布验证）、时区约定 |
| `tests/integration/` | 53 | 接口正常与边界、8 类业务拒绝、Redis 组件、5 条补偿路径 |
| `tests/concurrency/` | 7 | 不超卖、配额不被击穿、幂等、DB 唯一约束兜底 |

## 压测

```bash
python load_tests/run_benchmark.py
```

脚本会重置数据、以 4 个 worker 启动服务、按三档并发跑 Locust，跑完直接查库验证
不变量，最后生成 [`docs/benchmark.md`](docs/benchmark.md)。

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/activities` | 创建活动（201） |
| `GET` | `/api/activities/{activity_id}` | 查询活动配置 |
| `POST` | `/api/activities/{activity_id}/awards` | 配置奖品（201） |
| `POST` | `/api/lottery/draw` | 执行抽奖 |

三点容易踩的契约：

- 抽奖请求**必须带 `request_id`**（客户端生成的 UUID）。它是幂等键：重发同一个
  `request_id` 只会产生一次扣库存和一条订单，正在处理中的重复请求返回 409。
- 时间入参**必须带时区偏移**（如 `2026-09-14T18:00:00+08:00`）。不带偏移的值返回 422，
  不会被猜成 UTC。
- `success` 表示**流程是否正常完成**，不表示是否中奖。中奖和未中奖都是 `true`；
  业务拒绝才是 `false`，并带固定分类的 `reject_reason`。

请求/响应示例见 [`docs/REQUIREMENTS.md` §6](docs/REQUIREMENTS.md)。

## 目录

```text
lottery-engine/
├─ app/                  应用代码（interfaces / application / domain / infrastructure 分层）
├─ migrations/           Alembic 迁移
├─ docs/                 规划、需求规格、索引验证
├─ legacy/java/          已冻结的 Java 实现，仅作参考
├─ docker-compose.yml    MySQL + Redis
├─ alembic.ini
├─ requirements.txt
└─ .env.example
```

## 文档

| 文档 | 作用 |
| --- | --- |
| [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) | **规划**：项目定位、技术栈、架构原则、Phase 排期、停止线 |
| [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) | **需求规格**：功能需求、数据模型 DDL、API 契约、验收标准、已知缺陷 |
| [`DEVLOG.md`](DEVLOG.md) | **开发日志**：每阶段的关键决策、放弃的方案、踩过的坑、实测证据 |
| [`docs/db-explain.md`](docs/db-explain.md) | 索引验证：3 条主查询的 `EXPLAIN` 结果 |
| [`docs/benchmark.md`](docs/benchmark.md) | **压测报告**：吞吐、尾延迟、并发不变量（真实实测） |

冲突时以 `docs/PROJECT_PLAN.md` 为准。

## 当前进度

Phase 0–4 已完成：基线修复、MySQL 化、Redis 并发控制、pytest 测试体系、Locust 压测。

**已实测的并发不变量**（`uvicorn --workers 4`，4 个独立进程）：

| 验证项 | 结果 |
| --- | --- |
| 库存 100 / 并发 1000 | **恰好 100 次中奖，零超卖**；MySQL 与 Redis 库存均归零不为负 |
| 同一 `request_id` 并发 40 次 | 库中**只有 1 条订单**，库存只扣 1 |
| 同一用户 12 次并发 | 只放行 3 次（配置 10s/3 次）。进程内实现在 4 worker 下会放行 12 次 |
| Redis 宕机 | 抽奖返回 **503**，不降级放行；恢复后无需重启 |

**压测结果**（完整报告见 [`docs/benchmark.md`](docs/benchmark.md)）：

| 场景 | 并发 | RPS | P50 | P95 | 失败率 |
| --- | --- | --- | --- | --- | --- |
| Baseline | 50 | 90.9 | 220 ms | 1300 ms | 0.00% |
| Medium | 200 | 146.4 | 1100 ms | 1800 ms | 0.00% |
| Stress | 500 | 130.3 | 1400 ms | 9500 ms | 1.40% |

四档全部满足 `oversold = 0`、`duplicate order = 0`。Stress 档的失败全部是 503
（容量信号），没有一个 500。

> 服务端、MySQL、Redis、压测客户端全部跑在同一台笔记本上互相争抢 CPU。这些数字用于
> 横向比较不同配置，不代表架构的性能上限。压测过程中定位并修复了一个真实瓶颈：
> SQLAlchemy 连接池默认 5+10 在 200 并发下耗尽，详见 `docs/benchmark.md` 的瓶颈定位一节。

**尚未完成**：API 容器化与交付文档（Phase 5）、可选的 Celery 异步发奖（Phase 6）。

逐项验收标准见 [`docs/REQUIREMENTS.md` §8](docs/REQUIREMENTS.md)。

## Known Limitations

- **Redis 与 MySQL 是双写**，没有分布式事务。Redis 作闸门、MySQL 作账本，失败路径靠
  显式补偿而非两阶段提交。极端情况下（补偿本身失败）两者可能短暂漂移，
  下一次请求会用 MySQL 的剩余量重新初始化 Redis 计数。
- **Redis 不可用时整个抽奖不可用**（返回 503）。这是刻意选择：静默降级到进程内实现
  会在多 worker 下直接导致超卖，拒绝服务可恢复，超发的奖品不可回收。
- 单体部署，未做跨机房高可用。
- 中奖后的实际发奖尚未实现，订单停在 `award_state = pending`。

## Java 版（Legacy / Reference）

`legacy/java/` 是本项目最早的 Spring Boot 实现（Spring Boot 2.7、MyBatis、Redis、
RocketMQ、Dubbo）。自 2026-09-14 起**冻结**：不删除、不维护、不与 Python 版同步。

这套代码**从未成功编译或启动过**。缺陷记录在
[`docs/REQUIREMENTS.md` §9.2](docs/REQUIREMENTS.md)，**不计划修复**，其中最关键的两条：

- `legacy/java/src/main/resources/application.yml` 有两个顶层 `spring:` 键。Spring Boot 的
  YAML 加载器禁止重复键，启动即抛 `DuplicateKeyException`。这是历史上"8080 端口不监听"
  长期无解的真实原因——当时排查方向全在 MySQL/Redis 是否启动，没人看配置文件结构。
- `schema.sql` 里没有订单表，`ActivityPartakeImpl.recordDrawOrder()` 是空实现，
  抽奖不留任何记录。

保留它的用途只有一个：回答"为什么换技术栈"。

## 开发约定

- 不提交 `.venv/`、`.env`、本地数据库文件、Python 缓存、构建产物。
- 密码只放 `.env`，`.env.example` 里只放本地占位值。
- schema 只能通过 Alembic 迁移变更，不用 `create_all`。
- 阶段进度写进 `docs/REQUIREMENTS.md` 的验收清单，不在根目录堆临时 Markdown。
- **每完成一个 Phase，在 [`DEVLOG.md`](DEVLOG.md) 追加一节，与代码同一次提交**
  （格式见 [`docs/REQUIREMENTS.md` §10](docs/REQUIREMENTS.md)）。事后补写的决策记录必然失真。
  首次 clone 后执行一次，启用提交检查：

  ```bash
  git config core.hooksPath .githooks
  ```

  之后提交信息含 `phase-N` 但未改动 `DEVLOG.md` 时会被拒绝。
- **`requirements.txt` 与 `alembic.ini` 必须保持纯 ASCII。** pip 和 Alembic 都用系统 locale
  （本机是 GBK）解码这两个文件，中文注释会直接导致 `UnicodeDecodeError` 起不来。
  这个坑踩过两次，注释统一写英文。
