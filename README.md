# Lottery Engine

并发安全的营销抽奖服务。Python · FastAPI · MySQL · Redis。

---

## 1. 这是什么

营销活动里的抽奖服务：运营配置活动和奖品，用户在活动期内抽奖，系统按权重随机出奖、
扣减库存、落订单。

> "lottery" 在这里指**营销抽奖**（大转盘那种），不是彩票号码预测。

一次抽奖要同时满足的约束：

- 库存扣多了 → 奖品超发，真金白银的损失
- 用户双击或网络重试 → 不能扣两次库存、发两次奖
- 脚本刷接口 → 要挡住，但不能误伤正常用户
- 服务多进程部署 → 上面三条在跨进程时仍要成立

## 2. 为什么做这个项目

用一个范围受控的业务系统，证明这几项工程能力：数据库设计、缓存使用、并发正确性、
幂等、自动化测试、性能验证。

判断标准不是"功能多"，而是：**每一条技术主张都有可复现的测试或 benchmark 支撑**。
所以 README 里不会出现"支持高并发"这种没有数字的说法——能写进来的都在
[`docs/benchmark.md`](docs/benchmark.md) 里有对应的实测记录。

开发过程中的决策、放弃的方案和踩过的坑记在 [`DEVLOG.md`](DEVLOG.md)。

## 3. 架构

单体分层，不拆微服务——当前规模下拆分只会增加解释成本而不解决任何问题。

```text
                      Client / pytest / Locust
                                |
                                v
                +-------------------------------+
                |  FastAPI (uvicorn, N workers) |
                |        interfaces/api/        |
                +---------------+---------------+
                                |
                    application/lottery_process
                      （链路编排 + 失败补偿）
                                |
            +-------------------+-------------------+
            v                   v                   v
      domain/strategy      domain/models      infrastructure/
      加权抽奖算法          领域模型           repositories + redis/
            |                                       |
            +-------------------+-------------------+
                                |
              +-----------------+-----------------+
              v                                   v
      +---------------+                   +---------------+
      |     Redis     |                   |   MySQL 8.4   |
      |   —— 闸门 ——  |                   |   —— 账本 ——  |
      | Lua 原子扣库存 |                   | activity      |
      | ZSet 滑动窗口  |                   | award         |
      | request 幂等   |                   | draw_order    |
      +---------------+                   +---------------+
```

**Redis 是闸门，MySQL 是账本。** Redis 决定这次请求能不能继续（高并发下不放超），
MySQL 在事务里记录最终结果并用 `WHERE stock_surplus > 0` 兜底。两者可能因 Redis 被
清空而漂移，靠"按 MySQL 剩余量重新初始化"对齐。

## 4. 技术栈

| | 用途 |
| --- | --- |
| Python 3.11 / FastAPI | HTTP 服务，Pydantic 做请求与配置校验 |
| SQLAlchemy 2 / Alembic | ORM 与数据库迁移（schema 的唯一真源） |
| MySQL 8.4 | 业务数据，唯一约束 / 外键 / CHECK 约束 / 按查询设计的索引 |
| Redis 7 + Lua | 原子库存、滑动窗口限流、请求幂等 |
| pytest | 76 个用例，分 unit / integration / concurrency 三层 |
| Locust | 压测，产出可复现的 benchmark 报告 |
| Docker Compose | 一条命令拉起 MySQL + Redis + API |

## 5. 核心抽奖流程

```text
1.  幂等检查（request_id）   Redis SET NX，重复请求直接回放首次结果
2.  查活动                   MySQL，按 uk_activity_id
3.  状态 / 时间窗校验         status == running 且当前时间在有效期内
4.  频率限流（FR-6a）        Redis ZSet 滑动窗口，默认 10s / 3 次
5.  每日参与次数（FR-6b）     Redis 计数器，按 Asia/Shanghai 自然日重置
6.  扣活动库存                Redis Lua 原子判断 + 扣减
7.  取候选奖品                MySQL，stock_surplus > 0
8.  加权随机抽奖              纯内存，不依赖任何基础设施
9.  扣奖品库存                Redis Lua
10. 写库（单事务）            两处库存扣减 + 订单写入一起提交
11. 保存幂等结果
```

**第 4 步必须排在第 5 步之前。** 否则高频客户端在被限流拒绝的同时，还会把自己当天的
参与配额烧掉。

**任何已占用的资源，在后续步骤失败时必须按占用的逆序归还。** 第 6 步扣了活动库存，
若第 7–10 步任一失败，都要把活动库存和当日配额还回去。

## 6. 数据库设计

三张表：`activity` / `award` / `draw_order`。完整 DDL 见
[`docs/REQUIREMENTS.md` §4.2](docs/REQUIREMENTS.md)。

约束不只是装饰，每一条都在挡一类具体错误：

| 约束 | 挡住什么 |
| --- | --- |
| `uk_request_id` | 幂等的最后一道防线。即使 Redis 挂了或被清空，DB 仍拒绝重复订单 |
| `ck_activity_stock` / `ck_award_stock` | `stock_surplus >= 0`，库存不可能为负 |
| `ck_activity_time` | `end_time > start_time` |
| `fk_award_activity` | 奖品不能挂到不存在的活动上 |

索引按**真实查询**设计，每个都能回答"哪条查询需要它"，实测见
[`docs/db-explain.md`](docs/db-explain.md)：

| 索引 | 服务的查询 | EXPLAIN |
| --- | --- | --- |
| `uk_activity_id` | 抽奖第一步按业务键取活动 | `const` |
| `idx_activity_id` | 取候选奖品 | `ref` |
| `idx_user_activity_created` | 每日次数的 DB 兜底统计 | `range` + **`Using index`（覆盖索引）** |

第三条按「等值 → 等值 → 范围」排列，`COUNT(*)` 不需要回表。把 `created_at` 放前面，
前两个等值条件就用不上索引了。

`activity` 上**刻意没建** `(status, start_time, end_time)`：当前没有按状态扫描活动的
查询，没有查询支撑的索引就是装饰。

## 7. Redis 原子库存

为什么必须用 Lua：

```text
GET stock        <- 两个请求都读到 1
if stock > 0:
    DECR stock   <- 两个都扣，库存变成 -1
```

`DECR` 本身是原子的，但"判断 + 扣减"这个组合不是。Redis 单线程执行脚本，
把两步放进同一个脚本才原子。

**key 不存在时**用 `SET NX` 从 MySQL 的**剩余量**（不是总量）初始化后重试一次：

- 用 `NX`：并发下只有一个请求能写入初值，否则会覆盖别人已扣过的计数
- 用剩余量：Redis 被清空后从 MySQL 的当前进度续上，而不是把库存凭空恢复

**Redis 不可用时快速失败**，抽奖返回 503，不降级到进程内实现——进程内实现在多 worker
下根本不成立，静默降级只会把超卖问题藏起来。拒绝服务可恢复，超发出去的奖品不可回收。

## 8. 幂等

客户端为每次逻辑请求生成 `request_id`（UUID）。两层防线：

```text
Redis  SET idempotency:{request_id} processing NX EX 60
       +-- 抢到        -> 执行，完成后把结果写回供回放
       +-- processing  -> 409，有另一个请求正在处理
       +-- 已完成      -> 直接返回首次结果

MySQL  uk_request_id UNIQUE
       +-- 即使 Redis 挂掉 / 被清空 / TTL 过期，DB 仍拒绝第二条订单
```

执行失败时必须释放占位，否则一次偶发的数据库抖动会把那个 `request_id` 永久锁死。

**实测**：40 个线程并发发同一个 `request_id`，库中只有 1 条订单，库存只扣 1。

## 9. 限流

两条**不同**的规则，不能混为一谈：

| | 用途 | 实现 | 默认 |
| --- | --- | --- | --- |
| 频率限流（FR-6a） | 秒级防刷 | Redis ZSet 滑动窗口 + Lua | 10 秒 3 次 |
| 每日参与次数（FR-6b） | 日级业务配额 | Redis 计数器，key 带日期 | `activity.daily_limit` |

用 ZSet 而不是计数器：固定窗口计数器在边界会放过两倍流量（10s/3 次的配置下，
第 9.9 秒和第 10.1 秒各放 3 次）。ZSet 以时间戳为 score，每次先清窗口外的成员再计数。

ZSet 的 member 用 UUID 而不是时间戳——用时间戳会让同一刻的多次请求被 `ZADD` 去重成
一个，限流因此偏松。

**实测**：4 个 worker 进程下，同一用户 12 次并发请求只放行 3 次。
进程内实现在这个场景会放行 12 次。

## 10. 测试

```bash
pip install -r requirements.txt -r requirements-dev.txt
docker compose up -d
pytest                    # 全量 76 个
pytest -m concurrency     # 只跑并发用例（较慢）
```

跑在独立的 `lottery_test` 库与 Redis `db 1` 上；`conftest.py` 有断言保证跑错目标时
直接失败，而不是清空开发库。

| 层 | 用例 | 覆盖 |
| --- | --- | --- |
| `tests/unit/` | 16 | 抽奖算法（含 10 万次分布验证）、时区约定 |
| `tests/integration/` | 53 | 接口正常与边界、8 类业务拒绝、Redis 组件、5 条补偿路径 |
| `tests/concurrency/` | 7 | 不超卖、配额不被击穿、幂等、DB 唯一约束兜底 |

补偿路径用 monkeypatch 注入 MySQL 提交失败来构造——这类路径在正常流量下几乎不会发生，
但正是最容易写错、也最难在生产里发现的一类。

## 11. 压测

```bash
python load_tests/run_benchmark.py           # 全部四档
python load_tests/run_benchmark.py Stress    # 只跑一档，便于排查
```

脚本会重建数据、以 4 个 worker 启动服务、按档跑 Locust，跑完**直接查库验证不变量**，
最后生成 [`docs/benchmark.md`](docs/benchmark.md)。

两个刻意的设计：

- 每次请求用**全新的** `request_id` 与 `user_id`。前者复用会命中幂等缓存，
  后者复用会撞上限流——两种情况测的都不是抽奖链路本身。
- **业务拒绝不计入失败率**。库存不足、限流是系统的正确行为，算成 failure 会让这个
  指标失去诊断价值。

## 12. Benchmark 结果

环境：Windows 11 / 16 逻辑核 / MySQL 8.4 + Redis 7（Docker）/ `uvicorn --workers 4`。
**服务端、数据库、Redis、压测客户端全部跑在同一台笔记本上互相争抢 CPU。**

| 场景 | 并发 | 请求数 | RPS | P50 | P95 | 失败率 |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline | 50 | 5384 | 90.9 | 220 ms | 1300 ms | 0.00% |
| Medium | 200 | 8671 | 146.4 | 1100 ms | 1800 ms | 0.00% |
| Stress | 500 | 7728 | 130.3 | 1400 ms | 9500 ms | 1.40% |
| Contention | 200 | 7458 | 256.3 | 440 ms | 1100 ms | 0.13% |

**四档全部满足 `oversold = 0`、`duplicate order = 0`。**
Stress 档的失败全部是 503（容量信号），没有一个 500。

### 压测定位到的真实瓶颈

第一次跑时最大延迟 30929 ms——**正好是 SQLAlchemy `pool_timeout` 的默认值**。
日志坐实 `QueuePool limit of size 5 overflow 10 reached`。默认每进程只有 15 条连接，
4 worker 共 60 条，而 FastAPI 的同步端点跑在 40 线程的线程池里。

只改连接池做对照：

| pool + overflow | 4 worker 合计 | Stress RPS | Stress 失败 |
| --- | --- | --- | --- |
| 5 + 10（默认） | 60 | 49.2 | 372 |
| 20 + 10 | 120 | 73.3 | 312 |
| 40 + 20 | 240 | 108.2 | 246 |

**翻倍只换来 21% 的失败下降**，说明瓶颈已经转移：连接不是不够分，而是每条被占用得
更久（查询在饱和的 CPU 上变慢）。结论是**本机饱和点在 200 并发附近**，
而不是"再调大一点就好了"。

## 13. 快速开始

```bash
cp .env.example .env      # 8000 被占用的话改 API_HOST_PORT
docker compose up -d      # MySQL + Redis + API，迁移自动执行
```

| 页面 | 地址 | 给谁看 |
| --- | --- | --- |
| 抽奖页 | `http://127.0.0.1:8000/` | 用户。九宫格抽奖，**刻意不暴露中奖概率** |
| 开发者页 | `http://127.0.0.1:8000/dev` | 开发者。真实权重、请求响应原文、并发验证 |
| Swagger | `http://127.0.0.1:8000/docs` | 接口文档 |
| 健康检查 | `http://127.0.0.1:8000/api/health` | 探活 |

两个页面是刻意分开的。**抽奖页不展示任何概率信息**——九宫格里每个奖品占的格子数是
平均的（4 个奖品各占 2 格），奖品卡也不标中奖率，界面不泄露任何可用来反推概率的东西。
真实的 `weight` 只存在于后端，想看就去开发者页。

开发者页那边则把它全摊开：真实权重与归一化后的中奖率、请求响应原文，以及一个并发
验证面板——填任意并发数点「开始」，同时打出 N 个请求，跑完直接对账。勾上
「同一 request_id」可以现场看到幂等生效：100 个请求只产生 1 个订单、只扣 1 个库存。

首次使用需要先造一个活动（活动 ID 固定为 `100001`），用 Swagger 的
`POST /api/activities` 和 `POST /api/activities/{id}/awards` 各调一次即可。

本地开发（不跑 API 容器，用 uvicorn 热重载）：

```bash
docker compose up -d mysql redis
python -m venv .venv && .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

### 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/activities` | 创建活动（201） |
| `GET` | `/api/activities/{activity_id}` | 查询活动配置 |
| `GET` | `/api/activities/{activity_id}/awards` | 列出活动奖品（含已抽空的） |
| `POST` | `/api/activities/{activity_id}/awards` | 配置奖品（201） |
| `POST` | `/api/lottery/draw` | 执行抽奖 |

三点容易踩的契约：

- **`request_id` 必填**，客户端生成的 UUID。重发同一个只会产生一次副作用；
  正在处理中的重复请求返回 409。
- **时间入参必须带时区偏移**（如 `2026-09-14T18:00:00+08:00`）。不带偏移的值返回 422，
  不会被猜成 UTC。
- **`success` 表示流程是否正常完成，不表示是否中奖。** 中奖和未中奖都是 `true`；
  业务拒绝才是 `false`，并带固定分类的 `reject_reason`。

## 14. Known Limitations

明确边界不会让项目变弱，只会说明清楚它被验证到了什么程度。

- **Redis 与 MySQL 是双写，没有分布式事务。** Redis 作闸门、MySQL 作账本，失败路径靠
  显式补偿而非两阶段提交。极端情况下（补偿本身失败）两者可能短暂漂移，
  下一次请求会用 MySQL 的剩余量重新初始化 Redis 计数。
- **Redis 不可用时整个抽奖不可用**（返回 503）。这是刻意选择而非疏漏：静默降级到
  进程内实现会在多 worker 下直接导致超卖。
- **Benchmark 数字来自单台开发笔记本**，所有组件互相争抢 CPU。它用于横向比较不同配置
  （比如连接池调优前后），不代表该架构的性能上限。
- **中奖后的实际发奖尚未实现**，订单停在 `award_state = pending`。没有对接优惠券或
  物流服务。
- **单体部署**，未做跨机房高可用，没有服务发现、熔断、降级这些治理能力。
- 没有用户账号体系与鉴权，`user_id` 由调用方直接传入。
- 没有管理后台 UI，活动与奖品通过 API 配置。

## 15. Future Work

按优先级：

1. **异步发奖**（Celery + Redis）：中奖后写 pending 订单，由 worker 异步发放，
   支持重试与失败记录。需要 task 幂等——重复任务不能重复发奖。
2. **把压测客户端和依赖服务挪到独立机器**，测出不受本机 CPU 干扰的真实吞吐。
3. GitHub Actions 跑测试。
4. 活动状态扫描任务（到期自动关闭、清理 Redis 里已结束活动的 key）。

---

## 目录

```text
lottery-engine/
├─ app/                  应用代码（interfaces / application / domain / infrastructure）
├─ migrations/           Alembic 迁移
├─ tests/                unit / integration / concurrency
├─ load_tests/           locustfile + benchmark 编排
├─ docs/                 规划、需求规格、索引验证、压测报告
├─ docker/               镜像入口脚本、MySQL 初始化
├─ legacy/java/          已冻结的 Java 实现，仅作参考
├─ Dockerfile
└─ docker-compose.yml
```

## 文档

| 文档 | 作用 |
| --- | --- |
| [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) | 规划：定位、技术栈、Phase 排期、停止线 |
| [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) | 需求规格：FR/NFR、DDL、API 契约、验收标准 |
| [`DEVLOG.md`](DEVLOG.md) | 开发日志：每阶段的决策、放弃的方案、踩过的坑 |
| [`docs/benchmark.md`](docs/benchmark.md) | 压测报告 |
| [`docs/db-explain.md`](docs/db-explain.md) | 索引验证的 `EXPLAIN` 结果 |

冲突时以 `docs/PROJECT_PLAN.md` 为准。

## Java 版（Legacy / Reference）

`legacy/java/` 是最早的 Spring Boot 实现，自 2026-09-14 起**冻结**：不删除、不维护。

这套代码**从未成功编译或启动过**。最关键的两个缺陷（不计划修复）：

- `application.yml` 有两个顶层 `spring:` 键，Spring Boot 的 YAML 加载器禁止重复键，
  启动即抛 `DuplicateKeyException`。这是历史上"8080 端口不监听"长期无解的真实原因——
  当时排查方向全在 MySQL/Redis 是否启动，没人看配置文件结构。
- `schema.sql` 里没有订单表，`recordDrawOrder()` 是空实现，抽奖不留任何记录。

保留它的用途只有一个：回答"为什么换技术栈"。

## 开发约定

- 不提交 `.venv/`、`.env`、本地数据库文件、Python 缓存、构建产物。
- 密码只放 `.env`，`.env.example` 里只放本地占位值。
- schema 只能通过 Alembic 迁移变更，不用 `create_all`。
- **每完成一个 Phase，在 [`DEVLOG.md`](DEVLOG.md) 追加一节，与代码同一次提交。**
  首次 clone 后执行一次启用提交检查：

  ```bash
  git config core.hooksPath .githooks
  ```

- **`requirements.txt` 与 `alembic.ini` 必须保持纯 ASCII。** pip 和 Alembic 用系统
  locale（本机是 GBK）解码这两个文件，中文注释会导致 `UnicodeDecodeError`。踩过两次。
