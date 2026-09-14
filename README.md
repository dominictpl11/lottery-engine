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

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/activities` | 创建活动（201） |
| `GET` | `/api/activities/{activity_id}` | 查询活动配置 |
| `POST` | `/api/activities/{activity_id}/awards` | 配置奖品（201） |
| `POST` | `/api/lottery/draw` | 执行抽奖 |

两点容易踩的契约：

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
| [`docs/db-explain.md`](docs/db-explain.md) | 索引验证：3 条主查询的 `EXPLAIN` 结果 |

冲突时以 `docs/PROJECT_PLAN.md` 为准。

## 当前进度

Phase 0（基线修复）、Phase 1（MySQL 化 + 容器化）已完成。

**已具备**：MySQL 8.4 持久化、Alembic 迁移可从空库复现结构、唯一约束/外键/CHECK 约束、
按查询设计并验证过的索引、奖品库存与订单写入的事务边界、活动与奖品配置、加权抽奖、
频率限流、每日参与次数。

**已知尚未解决**（Phase 2 的全部内容）：

| | 现状 |
| --- | --- |
| 库存扣减 | 仍是 read-then-write，**并发下会超卖** |
| 限流与每日次数 | 仍是**进程内**实现，多 worker 各算各的，重启即失忆 |
| Redis | 容器已起，应用**尚未接入** |
| 幂等 | `draw_order.request_id` 的 UNIQUE 约束已就位，但值由服务端生成，**没有真正的幂等语义** |

之后是 Phase 3（pytest）、Phase 4（Locust benchmark）、Phase 5（交付）。
逐项验收标准见 [`docs/REQUIREMENTS.md` §8](docs/REQUIREMENTS.md)。

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
- **`requirements.txt` 与 `alembic.ini` 必须保持纯 ASCII。** pip 和 Alembic 都用系统 locale
  （本机是 GBK）解码这两个文件，中文注释会直接导致 `UnicodeDecodeError` 起不来。
  这个坑踩过两次，注释统一写英文。
