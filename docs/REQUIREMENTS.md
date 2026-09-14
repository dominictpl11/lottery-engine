# Lottery Engine 需求规格说明（Python 主线）

> 文档版本：v3.0
> 更新时间：2026-09-14
> 上位文档：[`PROJECT_PLAN.md`](PROJECT_PLAN.md)（下称 **v2**）

---

## 0. 文档说明

### 0.1 本文档与 v2 的关系

| | v2 规划文档 | 本文档 |
| --- | --- | --- |
| 回答 | 做什么、按什么顺序做、做到哪里停 | 做成什么样才算对 |
| 内容 | 定位、技术栈、架构原则、Phase 排期、简历口径 | 功能需求、数据模型、API 契约、非功能需求、验收标准 |
| 冲突时 | **以 v2 为准**；本文档同步修订 | — |

v2 负责"范围与节奏"，本文档负责"规格与验收"。两者不重复叙述。

### 0.2 术语

- **lottery** 在本项目中指**营销抽奖**（运营活动的转盘/抽奖），**不是**彩票号码预测。项目不涉及任何开奖数据抓取、号码统计或预测算法。
- **活动（Activity）**：一次运营抽奖活动，持有总库存和有效期。
- **奖品（Award）**：活动下的奖项，持有权重和独立库存。"谢谢参与"也是一个奖品（`award_type = none`）。
- **抽奖订单（DrawOrder）**：一次抽奖执行的持久化记录。
- **超卖（oversold）**：库存被扣成负数，或成功发出的奖品数超过配置库存。
- **幂等（idempotency）**：同一 `request_id` 重复到达，系统只执行一次副作用。

### 0.3 版本说明

v3.0 相对上一版（v1，2026-06-22）的变化：

- 项目定位从"将 Java 引擎重建为 Python 版"改为**Python 独立主线**，Java 版转 Legacy
- 异步发奖从 Celery + RabbitMQ 改为 **Celery + Redis**，且降级为可选（v2 §18）
- 新增 `request_id` 幂等机制（v1 只有"订单幂等"的模糊表述）
- 正式库从 SQLite 改为 **MySQL 8**
- 字段命名对齐 v2 §7（见 §4.1）
- 新增 §3 基线现状与 §8 已知缺陷清单

---

## 1. 范围

### 1.1 目标

用一个范围受控的抽奖系统，证明以下工程能力：数据库设计、缓存使用、并发正确性、幂等、自动化测试、性能验证。

判定标准不是"功能多"，而是：**每一条技术主张都有可复现的测试或 benchmark 支撑**。

### 1.2 In scope

活动配置、奖品配置、加权抽奖、订单持久化、库存一致性、频率限流、每日参与次数、请求幂等、pytest 测试体系、Locust 压测报告、Docker Compose 一键运行。

### 1.3 Out of scope

严格遵循 v2 §3.3。本项目**不引入**：Java 新功能、Spring Boot、Dubbo、RocketMQ、RabbitMQ、ZooKeeper、Kafka、Kubernetes、微服务拆分、Elasticsearch、Nacos、Service Mesh。

另外不做：管理后台 UI、用户账号体系与鉴权、真实奖品发放对接（优惠券/物流服务）、跨机房高可用、分布式事务框架。

### 1.4 Java 版状态

`legacy/java/`（Spring Boot 实现）自 v2 起为 **Legacy / Reference**：不删除、不维护、不要求与 Python 版同步、不再为本项目深入 Java 生态。

Java 版存在已知启动缺陷（见 §9.2），**不修复**。保留它的唯一用途是在面试中回答"为什么换技术栈"。

---

## 2. 角色与核心场景

| 角色 | 场景 |
| --- | --- |
| 运营（通过 API，无 UI） | 创建活动、配置奖品、查询活动配置 |
| 参与用户 | 在活动有效期内发起抽奖，得到中奖/未中奖结果 |
| 测试与压测脚本 | 以并发方式调用抽奖接口，验证库存与幂等不变量 |

---

## 3. 当前基线（2026-09-14 实测）

本节记录重启时的**真实起点**，供后续 Phase 估时参考。

### 3.1 可用的部分

`app/` 下的 FastAPI 服务可以启动，并跑通：建活动 → 配奖品 → 加权抽奖 → 订单落库 → Swagger。这是本项目唯一可运行的实现。

### 3.2 不可用 / 不正确的部分

- Redis 完全未接入：`enable_redis` / `redis_url` 是死配置，无任何代码读取
- 库存扣减、限流、每日次数三项**代码存在但实现不正确**，详见 §9.1 的 D1–D8
- 无测试、无迁移、无压测、无容器化

### 3.3 历史文档作废声明

原 `archive/2026-07-31/` 下的 24 份历史文档已于 2026-09-14 **整体删除**（内容可从 git 历史取回）。其中所有进度数字（"完成度 85%"、"95%"、"责任链 100%"）经代码核实**全部不成立**：Java 版从未编译成功，责任链是死代码，没有订单表。不得引用这些数字。

### 3.4 基线折算

对照 v2 §22 Definition of Done，当前真正达成约 **4 项**：服务可启动、健康检查、Swagger 可访问、订单可落库。

因此 v2 §20 的 **Phase 0 不是纯整理**，而是"整理 + 修复 D2/D3/D4/D6/D7"（见 §8.1）。

---

## 4. 数据模型规格

### 4.1 命名对齐

v2 §7 与现有代码存在命名冲突。**统一采用 v2 命名**，在 Phase 1 重建 MySQL schema 时一次性改完（此时成本最低）：

| v2 §7 | 现有代码 | 结论 |
| --- | --- | --- |
| `start_time` / `end_time` | `begin_time` / `end_time` | 用 v2 |
| `status` | `state` | 用 v2 |
| `stock_total` / `stock_surplus` | `stock_count` / `stock_surplus_count` | 用 v2 |
| `award_state` | `grant_state` | 用 v2 |
| award_type `coupon/physical/virtual/none` | `text/coupon/physical` | 用 v2，`none` = 谢谢参与 |
| `award_id`（业务键） | 不存在，仅有自增 `id` | 新增 |
| `request_id` | 不存在 | 新增，UNIQUE |

补充决定：

- `activity_id` / `award_id` 用 `BIGINT` 业务键（与 v2 §14.5 示例 `100001` / `101` 一致），另留自增 `id` 作代理主键。业务键对外，代理主键对内。
- `weight` 用 `INT` 而非 `FLOAT`。理由：浮点权重会让 §7.4 的统计分布测试引入不必要的精度误差，且整数权重在 Redis Lua 中更好处理。权重**不要求**是百分比，总和不必为 100。

### 4.2 DDL

```sql
-- 活动表
CREATE TABLE activity (
    id            BIGINT       NOT NULL AUTO_INCREMENT,
    activity_id   BIGINT       NOT NULL              COMMENT '业务活动ID',
    name          VARCHAR(100) NOT NULL,
    description   VARCHAR(255)     NULL,
    start_time    DATETIME     NOT NULL              COMMENT 'UTC',
    end_time      DATETIME     NOT NULL              COMMENT 'UTC',
    status        VARCHAR(16)  NOT NULL DEFAULT 'draft' COMMENT 'draft/running/closed',
    stock_total   INT          NOT NULL,
    stock_surplus INT          NOT NULL,
    daily_limit   INT          NOT NULL DEFAULT 3     COMMENT '每人每自然日参与次数上限',
    created_at    DATETIME     NOT NULL              COMMENT 'UTC，由应用写入',
    updated_at    DATETIME     NOT NULL              COMMENT 'UTC，由应用写入',
    PRIMARY KEY (id),
    UNIQUE KEY uk_activity_id (activity_id),
    CONSTRAINT ck_activity_stock CHECK (stock_surplus >= 0 AND stock_surplus <= stock_total),
    CONSTRAINT ck_activity_time  CHECK (end_time > start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 奖品表
CREATE TABLE award (
    id            BIGINT       NOT NULL AUTO_INCREMENT,
    award_id      BIGINT       NOT NULL              COMMENT '业务奖品ID',
    activity_id   BIGINT       NOT NULL,
    name          VARCHAR(100) NOT NULL,
    award_type    VARCHAR(16)  NOT NULL              COMMENT 'coupon/physical/virtual/none',
    content       VARCHAR(255)     NULL              COMMENT '券码/SKU/描述',
    weight        INT          NOT NULL,
    stock_total   INT          NOT NULL,
    stock_surplus INT          NOT NULL,
    created_at    DATETIME     NOT NULL              COMMENT 'UTC，由应用写入',
    updated_at    DATETIME     NOT NULL              COMMENT 'UTC，由应用写入',
    PRIMARY KEY (id),
    UNIQUE KEY uk_award_id (award_id),
    KEY idx_activity_id (activity_id),
    CONSTRAINT fk_award_activity FOREIGN KEY (activity_id) REFERENCES activity (activity_id),
    CONSTRAINT ck_award_stock  CHECK (stock_surplus >= 0 AND stock_surplus <= stock_total),
    CONSTRAINT ck_award_weight CHECK (weight > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 抽奖订单表
CREATE TABLE draw_order (
    id          BIGINT       NOT NULL AUTO_INCREMENT,
    order_id    VARCHAR(64)  NOT NULL,
    request_id  VARCHAR(64)  NOT NULL              COMMENT '幂等键，客户端生成',
    user_id     VARCHAR(64)  NOT NULL,
    activity_id BIGINT       NOT NULL,
    award_id    BIGINT           NULL              COMMENT '未中奖为 NULL',
    draw_state  VARCHAR(16)  NOT NULL              COMMENT 'won/missed/rejected',
    award_state VARCHAR(16)  NOT NULL              COMMENT 'pending/sent/failed/none',
    message     VARCHAR(255)     NULL,
    created_at  DATETIME     NOT NULL              COMMENT 'UTC，由应用写入',
    updated_at  DATETIME     NOT NULL              COMMENT 'UTC，由应用写入',
    PRIMARY KEY (id),
    UNIQUE KEY uk_order_id (order_id),
    UNIQUE KEY uk_request_id (request_id),
    KEY idx_user_activity_created (user_id, activity_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

时间戳由**应用**写入而非 `DEFAULT CURRENT_TIMESTAMP`：后者取 MySQL 服务器时区，
会让"库里都是 UTC"这条约定依赖部署环境。compose 里另外把 MySQL 钉成
`--default-time-zone=+00:00`，让手工 SQL 也落在同一口径上。

### 4.3 索引论证

v2 §8.3 要求每个索引都能回答"哪条查询需要它"。逐条论证：

| 索引 | 服务的查询 |
| --- | --- |
| `activity.uk_activity_id` | 抽奖主链路第一步 `WHERE activity_id = ?`；同时防止重复创建活动 |
| `award.idx_activity_id` | 候选奖品查询 `WHERE activity_id = ? AND stock_surplus > 0` |
| `award.uk_award_id` | 按业务奖品ID定位；防重复创建 |
| `draw_order.uk_order_id` | 订单号查询；防重复写入 |
| `draw_order.uk_request_id` | **幂等最后一道防线**：Redis 幂等检查异常时，数据库仍能阻止重复订单（v2 §8.2） |
| `draw_order.idx_user_activity_created` | 每日参与次数的 DB 兜底统计 `WHERE user_id = ? AND activity_id = ? AND created_at >= ?`；以及"我的参与记录"查询。三列顺序按等值→等值→范围排列 |

**刻意不建的索引**：`activity` 上不建 `(status, start_time, end_time)`。当前没有任何"按状态扫描活动列表"的查询，建了就是无查询支撑的装饰。若 Phase 6 引入活动状态扫描任务，再补建并在此登记。

`draw_order` 上暂不建 `award_state` 索引，同理——只有 Phase 6 的异步发奖 worker 需要扫 `pending`，届时再加。

### 4.4 时间与时区

- 数据库与应用内部**一律使用 UTC**，`DATETIME` 存 UTC 时刻
- 应用层使用 **timezone-aware** `datetime`（`datetime.now(timezone.utc)`），禁止 `datetime.utcnow()`（naive，且 3.12+ 已废弃）
- API 出入参使用 ISO 8601 带时区偏移的字符串，由 Pydantic 负责转换
- "每自然日"的日界以 **Asia/Shanghai** 计算（业务口径），需在实现中显式转换，不得直接用 UTC 日界

### 4.5 rejected 订单的持久化策略

为避免 D7 的刷库问题，区分两类拒绝：

| 情形 | 处理 |
| --- | --- |
| 参数非法 | HTTP 422（Pydantic），**不落库** |
| 活动不存在 | HTTP 404，**不落库** —— 否则任意 `activity_id` 都能写一行 |
| 业务拒绝（未运行 / 不在有效期 / 超每日次数 / 触发限流 / 库存不足） | HTTP 200 + `success=false`，**落 `draw_state=rejected` 订单** |

### 4.6 事务边界

对应 v2 §8.5。必须能明确回答"哪些操作在同一个数据库事务里，中间失败时系统处于什么状态"。

**单事务范围**（一次抽奖的 MySQL 写入）：

```text
BEGIN
  INSERT draw_order            -- 含 request_id，唯一约束在此生效
  UPDATE award.stock_surplus   -- 若中奖，且以 DB 为准的兜底扣减
COMMIT
```

订单写入与库存兜底扣减必须原子，否则会出现"订单说中奖但库存没扣"。

**刻意留在事务外的**：Redis 的库存扣减与幂等标记。Redis 不参与数据库事务，这是本项目
双写一致性问题的来源，**不用分布式事务解决**，改用显式补偿（FR-7）：

| 失败点 | 处理 |
| --- | --- |
| Redis 扣减成功、MySQL 事务失败 | 捕获异常 → Redis 库存补回 → 记 error log → 返回 500 |
| Redis 扣减成功、MySQL 成功、幂等结果写入失败 | 订单已落库，`uk_request_id` 保证重放不会产生第二条；幂等缓存缺失只会让重放走一次数据库查询 |
| Redis 不可用 | 按 FR-7 的降级策略处理，且必须在 README 的 Known Limitations 中说明 |

补偿路径本身必须有测试（见 §8.4）。

---

## 5. 功能需求

每条需求给出**可执行的判定方式**（一条 pytest 或一条 curl 能验证）。

### FR-1 活动管理

| | |
| --- | --- |
| 描述 | 通过 API 创建活动、查询活动配置。无管理后台 UI。 |
| 细则 | 活动字段见 §4.2。`status` 仅接受 `draft` / `running` / `closed`，由 Pydantic 枚举约束。创建时 `stock_surplus` 初始化为 `stock_total`。 |
| 判定 | `POST /api/activities` 返回 201 且库中存在该行；重复 `activity_id` 返回 409；`status` 传非法值返回 422；`end_time <= start_time` 返回 422。 |

### FR-2 奖品管理

| | |
| --- | --- |
| 描述 | 为活动配置多个奖品，每个奖品有独立权重与库存。 |
| 细则 | `award_type` 仅接受 `coupon` / `physical` / `virtual` / `none`。`weight` 必须为正整数。"谢谢参与"用 `award_type = none` 表示，它**算未中奖**（见 FR-3）。 |
| 判定 | `POST /api/activities/{activity_id}/awards` 返回 201；向不存在的活动配奖品返回 404；`weight <= 0` 返回 422。 |

### FR-3 抽奖主链路

| | |
| --- | --- |
| 描述 | 按 v2 §12 的 13 步执行一次抽奖。 |
| 顺序 | 参数校验 → 幂等检查 → 查活动 → 状态/时间校验 → **频率限流（FR-6a）** → **每日次数校验（FR-6b）** → Redis Lua 原子扣活动库存 → 取候选奖品 → 加权抽奖 → Lua 原子扣奖品库存 → 写 MySQL 订单 → 保存幂等结果 → 返回 |
| 顺序理由 | 频率限流必须排在每日次数**之前**：否则高频客户端在被限流拒绝的同时，还会把当日配额消耗掉。任何在配额消耗之后失败的步骤（库存不足等）都必须归还配额，与 FR-7 的库存补偿同一套纪律。 |
| 细则 | 候选奖品只包含 `stock_surplus > 0` 的行。抽中 `award_type = none` 的奖品时，`draw_state` 记为 `missed`、`award_state` 记为 `none`——**"谢谢参与"不得判为中奖**。 |
| 判定 | 见 §8.4（Phase 3）的 pytest 场景清单。 |

### FR-4 订单持久化

| | |
| --- | --- |
| 描述 | 每次实际执行的抽奖都生成一条订单。 |
| 细则 | `order_id` 由服务端生成且全局唯一。中奖 → `draw_state=won`、`award_state=pending`（未接异步发奖时直接为 `sent`，需在 README 说明）。未中奖 → `missed` + `none`。业务拒绝 → `rejected` + `none`。 |
| 判定 | 抽奖后库中订单数 +1；状态组合符合上表；`order_id` 唯一约束生效。 |

### FR-5 请求幂等

| | |
| --- | --- |
| 描述 | 同一 `request_id` 重复到达，只产生一次副作用（一次扣库存、一条订单、一次发奖）。 |
| 细则 | 客户端为每次逻辑请求生成 `request_id`（UUID）。Redis 侧 `SET idempotency:{request_id} processing NX EX 60`；已存在且已完成 → 返回首次结果；已存在且处理中 → 返回 409 或明确的"处理中"响应。MySQL 侧 `uk_request_id` 作为最后一道约束。 |
| 判定 | 并发发送 N 个相同 `request_id` 的请求，库中该 `request_id` 只有 1 条订单，且活动库存只减 1。 |

### FR-6 频率限流与每日次数（两个独立需求，不得混用）

现有代码把两者混为一谈（见 D2）。本文档明确拆分：

**FR-6a 频率限流（防滥用）**

| | |
| --- | --- |
| 描述 | 限制单用户在短时间窗口内的请求次数，防脚本刷。 |
| 细则 | Redis ZSet 滑动窗口，操作 `ZREMRANGEBYSCORE → ZCARD → ZADD → EXPIRE` 封装进单个 Lua 脚本以消除竞态。Key：`lottery:rate:{activity_id}:{user_id}`。窗口与阈值**可配置**（默认 10 秒 / 3 次），不得硬编码。 |
| 判定 | 窗口内超限被拒；窗口过后恢复；不同用户互不干扰；不同活动互不干扰。 |

**FR-6b 每日参与次数（业务规则）**

| | |
| --- | --- |
| 描述 | 限制单用户在单个活动内每自然日的参与次数，上限取 `activity.daily_limit`。 |
| 细则 | 与 FR-6a 是不同的东西：前者是秒级防刷，后者是日级业务配额。实现用 Redis 计数器，key 含日期（`lottery:daily:{activity_id}:{user_id}:{yyyymmdd}`），TTL 设到次日 Asia/Shanghai 零点。DB 侧可用 `idx_user_activity_created` 兜底核对。 |
| 判定 | `daily_limit=3` 时第 4 次被拒；跨日后配额重置；**不得出现"每分钟重置"的行为**（这正是 D2）。 |

### FR-7 库存一致性

| | |
| --- | --- |
| 描述 | 任何并发强度下，活动库存与奖品库存都不得为负，且成功发出的奖品不得超过配置库存。 |
| 细则 | Redis Lua 单脚本完成"判断 + 扣减"——`GET` 与 `DECR` 之间存在窗口，分成两条命令必然超卖。**活动库存扣减后若后续步骤失败（无可用奖品 / 奖品扣减失败 / MySQL 写入失败），必须按占用的逆序补偿回滚**（这正是 D3）。 |
| key 不存在 | 用 `SET NX` 从 MySQL 的**剩余量**（不是总量）初始化后重试一次。用 NX 是因为并发下只能有一个请求写入初值，否则会覆盖别人已扣过的计数；用剩余量是为了让 Redis 被清空后能从 MySQL 的当前进度续上，而不是把库存凭空恢复。 |
| Redis 不可用 | **快速失败**：抽奖接口返回 503，不降级到进程内实现。进程内实现在多 worker 下根本不成立，静默降级只会把超卖问题藏起来——拒绝服务是可恢复的，超发出去的奖品不是。健康检查不受影响，Redis 恢复后无需重启应用。 |
| 判定 | §8.4 的并发测试：初始库存 100、并发请求 1000，最终 `successful draws <= 100` 且 `stock >= 0`。 |

### FR-8 日志可追踪

| | |
| --- | --- |
| 描述 | 能凭 `request_id` 还原一次抽奖的完整链路。 |
| 细则 | 每条日志至少包含 v2 §19 的字段：`request_id` / `user_id` / `activity_id` / `order_id` / `draw_state` / `award_id` / `latency` / `error_type`。禁止记录密码、密钥。 |
| 判定 | `grep <request_id>` 能取到该次请求从进入到返回的全部关键节点。 |

---

## 6. API 契约

所有接口以 `/api` 为前缀。请求与响应均为 JSON；时间字段使用 ISO 8601 带时区偏移的字符串（见 §4.4）。

### 6.1 端点总览

| 方法 | 路径 | 说明 | 当前状态 |
| --- | --- | --- | --- |
| GET | `/api/health` | 健康检查 | 已实现 |
| POST | `/api/activities` | 创建活动 | 已实现 |
| GET | `/api/activities/{activity_id}` | 查询活动配置 | 已实现 |
| POST | `/api/activities/{activity_id}/awards` | 配置奖品 | 已实现 |
| POST | `/api/lottery/draw` | 执行抽奖 | 已实现；`request_id` 必填，由客户端提供 |

### 6.2 POST /api/lottery/draw

请求：

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_001",
  "activity_id": 100001
}
```

`request_id` 必填，由客户端（或压测脚本）为每次逻辑请求生成 UUID，是幂等键（FR-5）。

中奖响应（200）：

```json
{
  "success": true,
  "order_id": "1efca692bf94416898857ff0b23b42aa",
  "user_id": "user_001",
  "activity_id": 100001,
  "draw_state": "won",
  "award_state": "pending",
  "award": { "award_id": 101, "award_name": "100元优惠券" },
  "message": "中奖",
  "reject_reason": null
}
```

未中奖响应（200）—— 抽中 `award_type = none` 的"谢谢参与"：

```json
{
  "success": true,
  "order_id": "9e063e0bfe0142a88dee114642435cd8",
  "user_id": "user_001",
  "activity_id": 100001,
  "draw_state": "missed",
  "award_state": "none",
  "award": null,
  "message": "未中奖",
  "reject_reason": null
}
```

业务拒绝响应（200）：

```json
{
  "success": false,
  "order_id": "3a5b3cef50974e96a2baf7ebf5cdf06f",
  "user_id": "user_001",
  "activity_id": 100001,
  "draw_state": "rejected",
  "award_state": "none",
  "award": null,
  "message": "奖品已被抽完",
  "reject_reason": "award_stock_exhausted"
}
```

### 6.3 success 字段语义

`success` 表示**抽奖流程是否正常执行完毕**，不表示是否中奖：

| 情形 | `success` | `draw_state` |
| --- | --- | --- |
| 中奖 | `true` | `won` |
| 未中奖（含抽中 `award_type = none` 的"谢谢参与"） | `true` | `missed` |
| 业务拒绝 | `false` | `rejected` |

现有代码把"奖品库存不足"也返回 `success=true`（见 §9.1 末尾的附带语义问题），与上表不符，需一并修正。

### 6.4 HTTP 状态码

| 码 | 场景 |
| --- | --- |
| 200 | 抽奖执行完毕，**含业务拒绝** |
| 201 | 活动 / 奖品创建成功 |
| 404 | 活动或奖品不存在 |
| 409 | `activity_id` / `award_id` 已存在；或同一 `request_id` 正在处理中 |
| 422 | 参数校验失败（Pydantic） |
| 500 | 系统错误（含"Redis 已扣库存但 MySQL 写入失败并已补偿"的情形） |
| 503 | Redis 不可用。**刻意快速失败**，不降级放行——理由见 FR-7 |

**业务拒绝一律用 200，不用 4xx**（限流也不返回 429）。理由见 §7.2：压测的失败率只应统计系统错误；业务拒绝是系统的正确行为，混进 4xx 会让失败率指标失去意义。业务拒绝通过 `reject_reason` 单独计数。

### 6.5 reject_reason 取值

`activity_not_running` / `activity_not_in_window` / `daily_limit_exceeded` / `rate_limited` / `activity_stock_exhausted` / `award_stock_exhausted`

固定枚举，压测与测试按此分类统计。

---

## 7. 非功能需求

### 7.1 NFR-1 并发正确性（本项目的核心主张）

必须以自动化测试证明，不接受口头声明：

- `oversold = 0`
- `duplicate order = 0`
- 库存永不为负

### 7.2 NFR-2 性能口径

- 记录 RPS、平均延迟、P50、P95、P99、失败率（定义见 v2 §16.2）
- **失败率只统计系统错误（5xx / 连接失败），不统计正常业务拒绝**（库存不足、限流）。理由：业务拒绝是正确行为，计入失败率会让指标失去意义。业务拒绝单独计数。
- 压测必须记录测试环境（CPU / RAM / Python / MySQL / Redis 版本）
- **压测必须以多 worker 运行**（`uvicorn --workers 4` 或 gunicorn + uvicorn worker）。单进程下进程内限流器看起来"能用"，Redis 方案的必要性演示不出来，且 GIL 会让 RPS 失真。

### 7.3 NFR-3 可测试性

- 抽奖算法必须独立于 FastAPI / MySQL / Redis，可纯单元测试（v2 §5.3）
- 业务逻辑不得写在 Controller 中（v2 §5.2）
- 数据库访问经 Repository 封装
- 测试分三层：`tests/unit/`、`tests/integration/`、`tests/concurrency/`

### 7.4 NFR-4 抽奖算法测试要求

- **确定性测试**：固定随机种子，验证返回合法奖品、正确过滤零库存奖品、空奖品列表正常处理（返回未中奖而非抛异常）
- **统计测试**：10 万次模拟，实际分布与配置权重基本一致，允许合理随机误差（用相对误差阈值，不得要求精确相等）

### 7.5 NFR-5 配置与密钥

- 配置经 Pydantic Settings 从环境变量读取
- 提供 `.env.example`
- **禁止提交**：`.env`、数据库密码、API 密钥、本地数据库文件、venv、缓存、构建产物

### 7.6 NFR-6 可复现运行

`docker compose up` 一条命令起 MySQL + Redis + API。

---

## 8. 分阶段验收标准

对应 v2 §20 的 Phase 划分，并按 §3.4 的真实基线修正 Phase 0，按 §7.2 调整 Docker Compose 的位置。

### 8.1 Phase 0：基线整理与缺陷修复（预计 2–3 天）

> v2 原估 1–2 天，但那是按"纯整理"算的。实测基线（§3）要求同时修复 5 个正确性缺陷。

- [x] FastAPI 可启动，Swagger 可访问，基础抽奖链路可执行
- [x] 修复 **D2**（`daily_limit` 语义）、**D3**（活动库存泄漏）、**D4**（时区）、**D6**（枚举未绑定）、**D7**（脏请求落库）
- [x] 根 `README.md` 将 Java 段落标记为 Legacy
- [x] README 的功能描述改为诚实表述（不再声称"库存扣减和限流"已完成）
- [x] v2 文档移入 `docs/PROJECT_PLAN.md`
- [x] 更新 `DEVLOG.md`（§10）

### 8.2 Phase 1：MySQL 化 + 容器化（预计 3–5 天）

> **相对 v2 的调整**：把 Docker Compose 从 Phase 5 提前到这里。Phase 3 的集成/并发测试与 Phase 4 的 Locust 都依赖稳定可复现的 MySQL + Redis；手工起服务会导致 Phase 3–4 反复返工。Phase 5 只保留 API 容器化与 README。

- [x] SQLite → MySQL 8，按 §4.2 DDL 重建 schema（含 §4.1 的字段改名）
- [x] Alembic 建立，migration 可从空库复现完整结构
- [x] `docker-compose.yml` 提供 MySQL + Redis，`.env.example` 就位
- [x] 服务重启后数据仍在
- [x] 按 §4.6 落定事务边界，订单写入与库存兜底扣减在同一事务内
- [x] 对 §4.3 中至少 1–2 条主要查询执行 `EXPLAIN`，确认命中索引、无全表扫描 —— 3 条查询全部命中，结果见 [`db-explain.md`](db-explain.md)
- [x] 更新 `DEVLOG.md`（§10）

### 8.3 Phase 2：Redis 并发控制（预计 4–7 天）

- [x] Redis 客户端接入，**移除 D8 的死配置**
- [x] Lua 原子扣库存（活动 + 奖品），含 key 初始化与失败补偿（FR-7）
- [x] Redis ZSet + Lua 滑动窗口限流（FR-6a），窗口与阈值可配置
- [x] 每日参与次数独立实现（FR-6b）
- [x] `request_id` 幂等：Redis 主路径 + MySQL `uk_request_id` 兜底（FR-5）
- [x] 库存不会为负；重复请求不产生重复订单；多 worker 下限流状态共享 —— **已实测**：4 worker / 800 并发 / 库存 100 时恰好 100 次中奖；同一用户 12 次并发只放行 3 次（进程内实现在 4 worker 下会放行 12 次）
- [x] 更新 `DEVLOG.md`（§10）

### 8.4 Phase 3：pytest（预计 3–5 天）

**76 个用例全部通过**（unit 16 / integration 53 / concurrency 7）。
测试跑在独立的 `lottery_test` 库与 Redis db 1 上，与开发数据完全隔离。

- [x] **正常**：活动创建、奖品创建、正常抽奖、订单写入
- [x] **边界**：活动不存在、活动未开始、活动已结束、活动关闭、活动无库存、奖品无库存、触发限流、超每日次数、`request_id` 重复
- [x] **并发**：初始库存 100 / 并发 1000，验证 `successful == 100`、`stock >= 0`、无重复订单
- [x] **算法**：NFR-4 的确定性测试与统计测试（10 万次模拟，相对误差 < 5%）
- [x] **补偿路径**：注入 MySQL 提交失败，验证两处 Redis 库存与当日配额都被归还，且幂等占位被释放使该 `request_id` 可重试
- [x] 更新 `DEVLOG.md`（§10）

运行方式：

```bash
pip install -r requirements.txt -r requirements-dev.txt
docker compose up -d
pytest                    # 全量
pytest -m concurrency     # 只跑并发用例（较慢）
```

### 8.5 Phase 4：Locust + Benchmark（预计 2–4 天）

- [x] `load_tests/locustfile.py` + `load_tests/run_benchmark.py`（编排：重置环境 → 起多 worker → 跑三档 → 查库验不变量 → 生成报告）
- [x] 三档场景：50 / 200 / 500 并发，另加一档 `Contention`（库存 500 对 200 并发）专门验证不超卖
- [x] 多 worker 运行（NFR-2）：`uvicorn --workers 4`
- [x] 产出 [`docs/benchmark.md`](benchmark.md)，含测试环境、口径说明、瓶颈定位与业务结果分布
- [x] **`oversold = 0`、`duplicate order = 0`** —— 四档全部满足
- [x] 修复压测暴露的瓶颈：SQLAlchemy 连接池默认 5+10 在 200 并发下耗尽（`QueuePool limit ... timeout 30.00`），已调至 40+20 并把 MySQL `max_connections` 提到 500
- [x] 更新 `DEVLOG.md`（§10）

一条附带的语义修正：连接池耗尽由 500 改为 **503**。服务端本身没有出错，只是负载超过了
它能同时处理的量，这是容量信号而非缺陷；分开之后失败率才有诊断价值。

运行方式：

```bash
docker compose up -d
python load_tests/run_benchmark.py           # 全部四档
python load_tests/run_benchmark.py Stress    # 只跑一档，便于排查
```

### 8.6 Phase 5：README + 交付（预计 2–3 天）

- [x] API 容器化并入 compose —— `Dockerfile` + `docker/entrypoint.sh`，`docker compose up -d` 一条命令起 MySQL + Redis + API，迁移在 entrypoint 自动执行
- [x] README 按 v2 §23 的 15 节组织，含架构图、真实 benchmark、**Known Limitations**
- [x] 简历 bullet 按 §11 的口径落定 —— [`RESUME.md`](RESUME.md)，含"不能说的话"清单
- [x] 更新 `DEVLOG.md`（§10）

从空数据卷验证：`docker compose down -v && docker compose up -d` 后三服务全部 healthy、
迁移自动建表、容器内端到端抽奖成功且幂等生效。

### 8.7 Phase 6：可选（仅在前述全部完成且有余量时）

Celery + Redis 异步发奖；GitHub Actions。若进入本阶段，需补建 `draw_order.award_state` 索引并在 §4.3 登记。

---
- [ ] 更新 `DEVLOG.md`（§10）

## 9. 已知缺陷清单

### 9.1 Python 版（必须修）

| ID | 缺陷 | 位置 | 修复 Phase | 状态 |
| --- | --- | --- | --- | --- |
| **D1** | 库存扣减是 read-then-write（先读判 `>0`，再 `-=1`，再 commit），无原子语句 / 行锁 / 乐观锁 → 并发必超卖 | `app/infrastructure/repositories.py` | Phase 2（Lua 替代） | ✅ 已修复（Phase 2） |
| **D2** | **`daily_limit` 语义错误**：字段是"每人每日次数"，却以 `window_seconds=60` 传给滑动窗口 → 每日限制根本没实现，用户每分钟重置配额 | `app/application/lottery_process.py:35` | Phase 0（拆成 FR-6a/6b） | ✅ 已修复（Phase 0） |
| **D3** | **活动库存泄漏**：活动库存先扣（`:38`），之后若无可用奖品（`:43`）或奖品扣减失败（`:47`），**已扣的活动库存不回滚**，直接落 missed 订单 | `app/application/lottery_process.py:38-49` | Phase 0 | ✅ 已修复（Phase 0） |
| **D4** | 时区不一致：用 naive `datetime.utcnow()`（`:28`）比较 API 传入的时间；调用方按北京时间填写会被误判"不在有效期内" | `lottery_process.py:28,31` vs `domain/models.py:42-43` | Phase 0 | ✅ 已修复（Phase 0） |
| **D5** | 限流器内存无界增长：`defaultdict(deque)` 的 key 永不清理；`allow()` 的 check-then-append 无锁 | `app/infrastructure/limiters.py` | Phase 2（整体替换为 Redis） | ✅ 已修复（Phase 2） |
| **D6** | Pydantic schema 中 `state` / `award_type` 是裸 `str`，未绑定枚举 → 可写入任意非法值 | `app/schemas/activity.py:14,29` | Phase 0 | ✅ 已修复（Phase 0） |
| **D7** | "活动不存在"这类脏请求也写一行 `draw_order` → 可被刷库 | `lottery_process.py:54-56` | Phase 0（按 §4.5 处理） | ✅ 已修复（Phase 0） |
| **D8** | `enable_redis` / `redis_url` 是死配置，无任何代码读取；`redis` 依赖已装但 `app/` 下零 import | `app/core/config.py` | Phase 2 | ✅ 已修复（Phase 2） |

表中的文件/行号记录的是缺陷**原始位置**，用于追溯，修复后代码已变动。

附带的语义问题：

- ✅ 已随 Phase 0 修复：`success` 字段曾把"奖品库存不足"也返回 `True`，现按 §6.3 统一为「中奖/未中奖 → `true`，业务拒绝 → `false`」，并新增 `reject_reason`（§6.5）。
- ✅ 已随 Phase 1 修复：抽中"谢谢参与"（`award_type = none`）现记为 `missed` 而非中奖（FR-3），`AwardType` 已改名为 `coupon/physical/virtual/none`。

### 9.2 Java 版（不修，仅记录）

保留这些记录是为了能回答"为什么放弃 Java 版"：

1. `legacy/java/src/main/resources/application.yml` 存在**两个顶层 `spring:` 键**（第 6 行、第 72 行）。Spring Boot 的 YAML 加载器禁止重复键，启动即抛 `DuplicateKeyException`。这是当年"8080 端口不监听"卡了 7 个月的真实原因——当时的 4 份排障文档全在排查 MySQL / Redis 是否启动，没有人检查配置文件结构。
2. 同文件 RocketMQ 配置写在 `spring.rocketmq`，而 starter 读取的是顶层 `rocketmq:` → 配置不生效。
3. `schema.sql` 只有 4 张表，**没有任何订单表**；`ActivityPartakeImpl.recordDrawOrder()` 是空实现，直接 `return true`。抽奖不留任何记录。
4. `domain/rule/` 整包 8 个类是**死代码**——`IRuleEngine` 除自身外无任何引用，真正的校验硬编码在 `ActivityPartakeImpl` 中。
5. `legacy/java/pom.xml` 锁定 `java.version=1.8` + Spring Boot 2.7.14，与本机 `JAVA_HOME=JDK 21` 冲突。
6. 零测试（`src/test` 目录不存在）；`target/` 中无任何 `.class`，从未编译成功。

---

## 10. 开发日志（DEVLOG.md）

### 10.1 为什么要有

简历和面试考的不是"你用了哪些技术"，而是"你为什么这么选、放弃了什么、怎么证明它是对的"。
这些信息在代码里看不出来，在 commit message 里会随时间散掉。`DEVLOG.md` 是它们的唯一落点。

判断标准：**几个月后回头看，或者面试被追问某个设计时，能不能从这份文档直接答出来。**

### 10.2 每个 Phase 必须记录什么

| 项 | 要求 |
| --- | --- |
| 起点 | 这个阶段开始时系统是什么状态，为什么需要做它 |
| 关键决策 | 选了什么、**放弃了什么**、判断依据是什么。只写结论不写理由的条目没有价值 |
| 踩的坑 | 真实卡住过的问题和根因。这是最容易被追问、也最能体现深度的部分 |
| 实测证据 | 可复现的数字或验证结果。**不得写未实测的数字**（同 §11） |
| 产出 | commit 短 hash 与规模 |

### 10.3 规则

- **每完成一个 Phase 就追加一节，与该 Phase 的代码在同一次提交里。** 事后补写必然失真——
  踩过的坑当时记得，一周后只剩结论。
- 规格本身被修改时（例如 Phase 0 调整了 FR-3 的规则顺序），必须记录**为什么改规格**，
  而不是悄悄改掉。
- 不写流水账。"改了 X 文件"属于 git 的职责，不属于 DEVLOG。
- 与本文档冲突时，以本文档为准，并在 DEVLOG 中说明差异。

### 10.4 执行机制

三层，从软到硬：

1. `CLAUDE.md` —— 每个会话自动加载，约束"完成 Phase 必须更新 DEVLOG"。
2. 本文档 §8 各 Phase 的验收清单里都有"更新 DEVLOG.md"一条，不勾掉就不算完成。
3. `.githooks/pre-commit` —— 提交信息含 `phase-N` 但未同时改动 `DEVLOG.md` 时**拒绝提交**。
   启用方式见 [`README.md`](../README.md) 的开发约定。

---

## 11. 简历口径

严格遵循 v2 §24–25：

- 项目名用 **Lottery Engine — Concurrency-safe Marketing Lottery Service**
- 只有在**完成真实并发压测之后**，才可以使用 "High-Concurrency" 这个说法
- 技术栈只写真实用到的；`Redis Lua` / `Alembic` / `Celery` 需实际落地后才写入
- **不得填写未实测的数字**。所有 RPS / P95 / 并发数必须出自 `docs/benchmark.md` 中可复现的那一次测试

README 必须包含 **Known Limitations**（v2 §23）。明确说明边界不会让项目变弱：Redis 与 MySQL 仍是简化的双写一致性处理、单体部署、未做跨机房高可用、benchmark 为个人开发环境数据。

---

## 12. 停止线

本文档的验收标准全部达成后（对应 v2 §21 的 12 项 checklist），项目进入维护状态，不再新增技术栈。主要精力转回 City Quiz、ML/AI 能力、硕士申请与实习准备。
