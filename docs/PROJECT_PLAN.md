# Lottery Engine 项目规划文档（Python 主线版）

> 文档版本：v2.0  
> 更新时间：2026-09-14  
> 项目仓库：`dominictpl11/lottery-engine`  
> 项目定位：**面向硕士申请与 AI/算法实习的工程能力补充项目**
> 
> 核心原则：不再把本项目扩张成大型 Java 后端系统；以 Python 为主线，用一个范围受控的抽奖系统证明数据库、缓存、并发、一致性、测试与性能验证能力。

---

# 1. 项目定位

## 1.1 项目要证明什么

本项目不承担“AI 旗舰项目”的角色。

它的主要价值是证明：

1. 能用 Python 构建结构清晰的后端服务；
2. 能正确设计关系数据库与业务数据模型；
3. 理解 MySQL、事务、索引、唯一约束等数据库基础；
4. 理解 Redis 在库存、限流和幂等场景中的作用；
5. 能识别并解决并发下的超卖、重复请求、重复发奖等问题；
6. 能通过自动化测试与压力测试验证系统，而不是只声明“支持高并发”；
7. 能解释架构选择、失败场景和技术取舍。

本项目与 City Quiz 的关系：

- **City Quiz**：AI / LLM / RAG / 推荐 / Evaluation 主项目；
- **Lottery Engine**：Backend / MySQL / Redis / Concurrency / Testing 工程项目。

两个项目共享 Python 后端基础，但分别向 AI 与系统工程方向延伸。

---

# 2. 当前项目状态

仓库目前同时存在 Java 和 Python 两套实现。

## 2.1 Java 版本

当前 Java 版本使用过：

- Spring Boot
- MyBatis
- MySQL
- Redis
- RocketMQ
- Dubbo

从 v2.0 开始：

> **Java 版本进入 Legacy / Reference 状态。**

后续原则：

- 不删除已有 Java 代码；
- 不再要求 Java 与 Python 功能同步；
- 不继续为了本项目深入 Spring、Dubbo、RocketMQ、ZooKeeper 等 Java 后端生态；
- 如未来重新投 Java 后端岗位，再单独恢复维护。

Java 版本不作为当前简历的主要技术叙事。

---

## 2.2 Python 版本

当前 Python 版本已经具备：

- FastAPI API 服务；
- SQLAlchemy ORM；
- 活动、奖品、订单等基础模型；
- 加权随机抽奖；
- 活动有效性判断；
- 基础库存扣减；
- 进程内滑动窗口限流；
- SQLite 本地运行能力；
- Redis Python 依赖。

目前仍属于 **MVP / Baseline**。

当前关键不足：

1. 正式数据库仍需迁移到 MySQL；
2. 库存扣减仍需解决并发原子性；
3. 限流仍需从进程内实现升级到 Redis；
4. 缺少完整幂等机制；
5. 缺少系统化 pytest 测试；
6. 缺少 Locust 压测及结果报告；
7. 缺少 Docker Compose 一键运行环境；
8. README 尚需形成明确的架构、测试与 benchmark 证据。

因此，后续开发目标不是继续增加大量业务功能，而是：

> **把一个能运行的简单实现，升级成一个可验证、可解释的工程系统。**

---

# 3. 最终技术栈

## 3.1 核心技术栈

| 技术             | 用途                         | 是否必须 |
| -------------- | -------------------------- | ---- |
| Python 3.11+   | 主开发语言                      | 必须   |
| FastAPI        | REST API 服务                | 必须   |
| Pydantic       | 请求、响应、配置校验                 | 必须   |
| SQLAlchemy 2.x | ORM 与数据库访问                 | 必须   |
| MySQL 8.x      | 正式关系型业务数据库                 | 必须   |
| Redis          | 库存、限流、幂等                   | 必须   |
| Redis Lua      | 原子库存操作                     | 必须   |
| pytest         | 单元测试、集成测试                  | 必须   |
| Locust         | 并发压力测试                     | 必须   |
| Docker Compose | 本地一键启动 MySQL / Redis / API | 必须   |
| Alembic        | 数据库 Migration              | 推荐   |

## 3.2 可选技术

| 技术                   | 用途     | 何时增加        |
| -------------------- | ------ | ----------- |
| Celery + Redis       | 异步发奖   | 核心链路完成后仍有时间 |
| GitHub Actions       | 自动执行测试 | 项目收尾阶段      |
| Prometheus / Grafana | 监控     | 不作为当前要求     |

## 3.3 明确不做

当前版本不为了“技术栈丰富”引入：

- Java 新功能；
- Spring Boot 新模块；
- Dubbo；
- RocketMQ；
- RabbitMQ；
- ZooKeeper；
- Kafka；
- Kubernetes；
- 微服务拆分；
- Elasticsearch；
- Nacos；
- Service Mesh。

这些技术并不是永远没有价值，而是当前无法明显提高本项目对硕士申请和 AI/算法实习的边际价值。

---

# 4. 总体架构

```text
                     Client / Test / Locust
                              |
                              | HTTP
                              v
                     +-----------------+
                     |     FastAPI     |
                     +--------+--------+
                              |
                      Application Layer
                              |
               +--------------+--------------+
               |              |              |
               v              v              v
          Rule Check      Draw Strategy    Order Service
               |              |              |
               +--------------+--------------+
                              |
               +--------------+--------------+
               |                             |
               v                             v
            Redis                          MySQL
     - Atomic Stock                  - Activity
     - Rate Limit                    - Award
     - Idempotency                   - Draw Order
     - Short-lived State             - Persistent State
```

可选异步发奖：

```text
Draw Success
     |
     v
Persist Pending Order
     |
     v
Celery Task
     |
     v
Award Worker
     |
     +--> success -> SENT
     |
     +--> failure -> retry -> FAILED
```

---

# 5. 架构原则

## 5.1 保持单体

项目采用单体架构。

原因：

- 项目规模有限；
- 当前重点是业务正确性而不是分布式服务治理；
- 更容易测试和解释；
- 避免 AI 生成大量无必要的微服务模板代码。

单体不代表所有代码写在一个文件里。

仍然按照职责分层：

```text
API / Interface
      |
Application Service
      |
Domain Logic
      |
Infrastructure
```

---

## 5.2 业务逻辑不能堆在 Controller

Controller 只负责：

- 接收请求；
- Pydantic 校验；
- 调用 Application Service；
- 转换响应；
- 处理 HTTP 层异常。

抽奖逻辑、库存逻辑、限流逻辑、幂等逻辑不得直接写入 Controller。

---

## 5.3 抽奖算法与基础设施分离

抽奖概率算法应独立于：

- FastAPI；
- MySQL；
- Redis。

例如：

```python
class DrawStrategy:
    def draw(self, awards: list[AwardCandidate]) -> AwardCandidate | None:
        ...
```

这样可以直接通过 pytest 测试概率算法。

---

# 6. 推荐目录结构

```text
lottery_python/
├── app/
│   ├── main.py
│   │
│   ├── interfaces/
│   │   └── api/
│   │       ├── activity_controller.py
│   │       ├── award_controller.py
│   │       └── lottery_controller.py
│   │
│   ├── application/
│   │   ├── activity_service.py
│   │   ├── lottery_service.py
│   │   └── award_service.py
│   │
│   ├── domain/
│   │   ├── models.py
│   │   ├── strategy/
│   │   │   └── draw_algorithm.py
│   │   └── rules/
│   │       ├── activity_rule.py
│   │       ├── stock_rule.py
│   │       └── participation_rule.py
│   │
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   └── repositories.py
│   │   ├── redis/
│   │   │   ├── client.py
│   │   │   ├── inventory.py
│   │   │   ├── rate_limiter.py
│   │   │   └── idempotency.py
│   │   └── tasks/
│   │       └── award_tasks.py       # Optional
│   │
│   ├── schemas/
│   │   ├── activity.py
│   │   ├── award.py
│   │   └── lottery.py
│   │
│   └── core/
│       ├── config.py
│       ├── logging.py
│       └── exceptions.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── concurrency/
│
├── load_tests/
│   └── locustfile.py
│
├── migrations/
├── docker-compose.yml
├── requirements.txt
├── README.md
└── PROJECT_PLAN.md
```

不要求为了完全匹配目录结构而大规模重写现有代码。

原则是：

> **现有结构能清晰表达职责就保留，只在真正需要时重构。**

---

# 7. 核心业务模型

## 7.1 Activity

建议字段：

```text
id
activity_id
name
description
start_time
end_time
status
stock_total
stock_surplus
daily_limit
created_at
updated_at
```

状态：

```text
draft
running
closed
```

必须验证：

- 活动存在；
- 状态为 running；
- 当前时间位于有效期；
- 活动仍有库存。

---

## 7.2 Award

建议字段：

```text
id
award_id
activity_id
name
award_type
content
weight
stock_total
stock_surplus
created_at
updated_at
```

奖品类型：

```text
coupon
physical
virtual
none
```

`none` 可表示谢谢参与。

---

## 7.3 DrawOrder

建议字段：

```text
id
order_id
request_id
user_id
activity_id
award_id
draw_state
award_state
created_at
updated_at
```

`request_id` 用于请求幂等。

抽奖状态：

```text
won
missed
rejected
```

发奖状态：

```text
pending
sent
failed
none
```

---

# 8. MySQL 设计目标

本项目使用 MySQL，不只是因为“需要一个数据库”，而是要能够证明自己理解关系数据库的基本工程用法。

至少应实践以下能力：

## 8.1 Schema 设计

需要自己理解：

- 主键；
- 外键或逻辑关联；
- NOT NULL；
- UNIQUE；
- 索引；
- 时间字段；
- 状态字段；
- 数据类型选择。

---

## 8.2 唯一约束

例如对 `request_id` 建立 UNIQUE：

```sql
UNIQUE KEY uk_request_id (request_id)
```

作用：

> 即使 Redis 幂等检查发生异常，数据库仍然可以作为最后一道防止重复订单的约束。

是否增加：

```text
(user_id, activity_id)
```

唯一约束取决于业务规则。

如果允许每人每天多次参与，就不能简单限制一个用户一个活动只有一条订单。

因此约束必须与真实业务一致，不能为了展示技术随意增加。

---

## 8.3 Index

应根据真实查询设计索引，例如：

```text
activity_id
user_id
request_id
(user_id, activity_id, created_at)
status
created_at
```

每个索引都应能够回答：

> 哪条查询需要它？

---

## 8.4 EXPLAIN

至少选择 1–2 个主要查询使用：

```sql
EXPLAIN ...
```

观察：

- 是否命中索引；
- 扫描行数；
- 查询类型；
- 是否存在明显全表扫描。

README 中可以保存一小段真实优化案例。

---

## 8.5 Transaction

需要明确哪些操作必须处于同一个数据库事务中。

例如：

```text
创建抽奖订单
+
更新最终业务状态
```

必须能够解释：

> 如果中间一步失败，系统应该处于什么状态？

不要求实现复杂分布式事务，但要理解事务边界。

---

# 9. Redis 设计

Redis 在本项目中不是“为了简历加一个 Redis”。

必须承担明确职责。

---

## 9.1 原子库存扣减

目标：

> 多个请求同时抽奖时，库存不能被扣成负数。

错误的简单实现：

```text
GET stock
if stock > 0:
    DECR stock
```

因为 GET 与 DECR 之间可能插入其他请求。

推荐采用 Redis Lua：

```text
读取库存
  |
库存 <= 0 ? ---- yes ---> 返回失败
  |
 no
  |
库存 - 1
  |
返回成功
```

整个 Lua 脚本作为一次 Redis 原子操作执行。

要求：

- 活动库存不能为负；
- 奖品库存不能为负；
- 测试高并发请求；
- 记录测试结果。

---

## 9.2 Redis Lua 示例逻辑

伪代码：

```lua
local stock = tonumber(redis.call('GET', KEYS[1]))

if stock == nil or stock <= 0 then
    return 0
end

redis.call('DECR', KEYS[1])
return 1
```

实际实现时还需考虑：

- Key 不存在；
- 初始化；
- Redis 异常；
- MySQL 与 Redis 数据同步；
- 活动关闭后的 Key 清理。

本项目不要求构建复杂分布式缓存一致性框架。

---

# 10. 限流

当前 Baseline 使用进程内滑动窗口。

目标版本升级为：

> **Redis ZSet Sliding Window Rate Limiting**

例如用户每 10 秒最多请求 3 次：

```text
ZREMRANGEBYSCORE
ZCARD
ZADD
EXPIRE
```

最好将相关操作封装成 Lua，减少竞态。

Key 示例：

```text
lottery:rate:{activity_id}:{user_id}
```

必须测试：

- 限制生效；
- 时间窗口过后恢复；
- 不同用户互不干扰；
- 不同活动互不干扰。

---

# 11. 幂等设计

## 11.1 为什么需要幂等

用户可能因为：

- 双击；
- 网络重试；
- 浏览器自动重发；
- 上游服务重试；

导致同一个请求多次到达系统。

如果没有幂等：

```text
一次点击
↓
两个请求
↓
扣两次库存
↓
生成两个订单
↓
发两次奖
```

---

## 11.2 request_id

客户端或测试脚本为每一次逻辑请求生成：

```text
request_id
```

例如：

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_001",
  "activity_id": 100001
}
```

Redis：

```text
SET idempotency:{request_id} processing NX EX 60
```

如果 Key 已存在：

- 已完成：返回之前结果；
- 正在处理：拒绝重复执行或等待策略。

MySQL：

```text
request_id UNIQUE
```

作为最终约束。

---

# 12. 核心抽奖流程

最终主链路建议：

```text
1. 接收 draw request
       |
2. Pydantic 参数校验
       |
3. 幂等检查
       |
4. 查询活动
       |
5. 活动状态 / 时间校验
       |
6. Redis 用户限流
       |
7. Redis Lua 原子扣减活动库存
       |
8. 获取可用奖品
       |
9. Weighted Draw
       |
10. 若中奖，原子扣减对应奖品库存
       |
11. MySQL 创建 DrawOrder
       |
12. 保存幂等结果
       |
13. 返回结果
```

需要专门考虑：

```text
Redis 库存已经扣减
        |
MySQL 写订单失败
```

个人项目不需要立即构造复杂分布式事务。

可以采用明确且可解释的补偿策略，例如：

1. 捕获数据库异常；
2. Redis 库存补回；
3. 记录 error log；
4. 返回系统错误。

然后通过测试验证该补偿路径。

重点是：

> 能够意识到双写一致性问题，并明确说明自己的简化方案和限制。

---

# 13. 抽奖算法

第一版使用 Weighted Random Draw。

示例：

```text
一等奖 weight = 1
二等奖 weight = 9
三等奖 weight = 20
谢谢参与 weight = 70
```

总权重：

```text
100
```

不要求权重必须是百分比。

测试要求：

## 13.1 确定性测试

通过固定 Random Seed 测试：

- 返回合法奖品；
- 过滤无库存奖品；
- 空奖品列表正常处理。

## 13.2 统计测试

运行大量模拟：

```text
100,000 draws
```

验证实际分布与配置权重基本一致。

统计测试需要允许合理随机误差，不能要求精确相等。

---

# 14. API 设计

## 14.1 Health

```http
GET /api/health
```

---

## 14.2 创建活动

```http
POST /api/activities
```

---

## 14.3 创建奖品

```http
POST /api/activities/{activity_id}/awards
```

---

## 14.4 查询活动

```http
GET /api/activities/{activity_id}
```

---

## 14.5 抽奖

```http
POST /api/lottery/draw
```

请求：

```json
{
  "request_id": "uuid",
  "user_id": "user_001",
  "activity_id": 100001
}
```

响应：

```json
{
  "success": true,
  "order_id": "202609140001",
  "draw_state": "won",
  "award": {
    "award_id": 101,
    "award_name": "100元优惠券"
  }
}
```

---

# 15. pytest 测试规划

测试是本项目的重要组成部分。

最终至少包含：

```text
tests/
├── unit/
│   ├── test_draw_algorithm.py
│   ├── test_activity_rules.py
│   └── test_idempotency_logic.py
│
├── integration/
│   ├── test_activity_api.py
│   ├── test_draw_api.py
│   ├── test_mysql_repository.py
│   └── test_redis_inventory.py
│
└── concurrency/
    ├── test_stock_never_negative.py
    └── test_duplicate_request.py
```

---

## 15.1 必须验证的场景

### 正常场景

- 活动创建成功；
- 奖品创建成功；
- 正常抽奖；
- 订单成功写入。

### 边界场景

- 活动不存在；
- 活动未开始；
- 活动已结束；
- 活动关闭；
- 无库存；
- 奖品无库存；
- 用户触发限流；
- request_id 重复。

### 并发场景

例如：

```text
Initial stock = 100
Concurrent requests = 1,000
```

最终必须满足：

```text
successful stock consumption <= 100
stock >= 0
duplicate request does not create duplicate order
```

---

# 16. Locust 压力测试

Locust 用于回答：

> 系统在大量用户同时请求时表现怎么样？

不能仅写“support high concurrency”。

必须有真实数据。

---

## 16.1 测试场景

建议至少做三个场景：

### Baseline

```text
50 concurrent users
```

### Medium

```text
200 concurrent users
```

### Stress

```text
500 / 1000 concurrent users
```

最终数字根据本机环境调整。

---

## 16.2 记录指标

必须记录：

- Requests / second；
- Average latency；
- P50；
- P95；
- P99；
- Failure rate；
- successful draws；
- final Redis stock；
- final MySQL order count；
- oversold count；
- duplicate order count。

---

## 16.3 Benchmark 报告

建立：

```text
docs/benchmark.md
```

格式示例：

```text
Environment:
CPU:
RAM:
Python:
MySQL:
Redis:

Initial Stock:
Concurrent Users:
Total Requests:

RPS:
P50:
P95:
P99:
Failure Rate:

Oversold:
Duplicate Orders:
```

简历中只能使用真实测得的数据。

---

# 17. Docker Compose

目标：

```bash
docker compose up
```

即可启动：

```text
MySQL
Redis
FastAPI
```

可选再启动：

```text
Celery Worker
```

必须通过 `.env.example` 提供配置模板。

禁止提交：

- 数据库密码；
- API 密钥；
- 本地数据库文件；
- `.env`；
- Python venv；
- cache；
- build artifacts。

---

# 18. 可选：异步发奖

异步发奖不是项目 P0。

只有以下内容完成后再考虑：

- MySQL；
- Redis Lua 库存；
- Redis 限流；
- 幂等；
- pytest；
- Locust；
- Docker。

如果有时间，采用：

> **Celery + Redis**

不额外加入 RabbitMQ。

流程：

```text
中奖
 |
创建 pending order
 |
Celery Task
 |
Worker 发奖
 |
 +--> success -> sent
 |
 +--> retry
 |
 +--> max retries -> failed
```

需要支持：

- retry；
- worker 重启；
- task 幂等；
- 重复任务不能重复发奖。

---

# 19. 日志

至少记录：

```text
request_id
user_id
activity_id
order_id
draw_state
award_id
latency
error_type
```

不能记录敏感密码或密钥。

日志目的主要是：

> 能根据 request_id 追踪一次抽奖链路。

不需要当前阶段建设复杂 ELK 系统。

---

# 20. 开发阶段

## Phase 0：整理现有 Python Baseline

目标：

- 确保现有 FastAPI 版本可以正常运行；
- 确保当前活动 / 奖品 / 抽奖链路可执行；
- 清理 README 与无用文件；
- Java 标记为 Legacy。

验收：

```text
FastAPI starts
Swagger works
Basic draw works
```

预计：1–2 天。

---

## Phase 1：MySQL 化

任务：

- SQLite -> MySQL；
- SQLAlchemy 配置；
- 建立 Alembic；
- 检查 schema；
- 添加必要 unique constraint / index；
- 使用 EXPLAIN 检查关键查询。

验收：

- 所有核心数据写入 MySQL；
- 重启服务后数据仍存在；
- migration 可复现数据库结构。

预计：2–4 天。

---

## Phase 2：Redis 并发控制

任务：

- Redis 客户端；
- 活动库存缓存；
- Redis Lua 原子扣库存；
- Redis ZSet 限流；
- request_id 幂等。

验收：

- 库存不会为负；
- 重复请求不会生成重复订单；
- 多实例理论上仍可共享限流状态。

预计：4–7 天。

---

## Phase 3：pytest

任务：

- 单元测试；
- API 集成测试；
- Redis / MySQL 测试；
- 并发测试。

验收：

- 核心路径全覆盖；
- 边界场景有自动化验证。

预计：3–5 天。

---

## Phase 4：Locust + Benchmark

任务：

- locustfile；
- 不同并发级别测试；
- 收集结果；
- 修复明显瓶颈；
- 输出 benchmark report。

验收：

- 至少一份可复现的压测报告；
- oversold = 0；
- duplicate order = 0。

预计：2–4 天。

---

## Phase 5：Docker + README + CV

任务：

- Docker Compose；
- 架构图；
- README；
- Benchmark；
- Demo；
- 简历 bullet。

预计：2–3 天。

---

## Phase 6：Optional

如果前面全部完成且仍有时间：

- Celery + Redis 异步发奖；
- GitHub Actions。

否则停止。

---

# 21. 项目停止线

本项目的目的不是无限扩张。

达到以下条件以后，应停止新增技术栈，并把主要时间转向：

- City Quiz；
- ML / AI 项目；
- 硕士申请；
- AI / 算法实习准备。

停止线：

- [ ] Python/FastAPI 主链路稳定；
- [ ] MySQL 正式使用；
- [ ] Redis + Lua 原子库存完成；
- [ ] Redis 限流完成；
- [ ] request_id 幂等完成；
- [ ] 关键 MySQL constraint / index 完成；
- [ ] pytest 核心测试完成；
- [ ] Locust benchmark 完成；
- [ ] Docker Compose 可启动；
- [ ] README 有架构图；
- [ ] README 有真实 Benchmark；
- [ ] 自己能解释系统完整链路。

完成以后：

> **Lottery Engine 进入维护状态，不继续堆技术。**

---

# 22. Definition of Done

只有同时满足以下条件，项目才可以正式称为：

> **Concurrency-safe Lottery Engine**

而不是简单写“High-Concurrency System”。

## 功能

- 活动配置；
- 奖品配置；
- 加权抽奖；
- 订单记录；
- 库存控制；
- 限流；
- 幂等。

## 数据库

- MySQL；
- 合理 schema；
- unique constraint；
- index；
- transaction；
- 至少一次 EXPLAIN 分析。

## Redis

- Lua 原子库存；
- 分布式限流；
- 幂等状态。

## 测试

- pytest 单测；
- integration test；
- concurrency test。

## 性能

- Locust；
- 有明确测试环境；
- 有真实 P95 / P99；
- oversold = 0；
- duplicate order = 0。

## 工程

- Docker Compose；
- `.env.example`；
- README；
- 架构图；
- Benchmark Report。

---

# 23. README 最终应包含

```text
1. What is Lottery Engine?
2. Why this project?
3. Architecture
4. Tech Stack
5. Core Draw Flow
6. Database Design
7. Redis Inventory Design
8. Idempotency
9. Rate Limiting
10. Testing
11. Load Testing
12. Benchmark Results
13. Quick Start
14. Known Limitations
15. Future Work
```

特别增加：

## Known Limitations

例如：

- Redis 与 MySQL 仍存在简化的双写一致性处理；
- 单体部署；
- 未做跨机房高可用；
- Benchmark 为个人开发环境测试；
- 不代表生产级大型营销平台。

明确限制不会让项目变弱，反而说明理解工程边界。

---

# 24. 简历定位

建议项目名称：

> **Lottery Engine — Concurrency-safe Marketing Lottery Service**

或：

> **High-Concurrency Lottery Engine**

只有完成真实并发测试后才使用第二个名字。

技术栈：

```text
Python, FastAPI, MySQL, Redis, SQLAlchemy, pytest, Locust, Docker
```

如果真实使用：

```text
Redis Lua
Alembic
Celery
```

再写入。

---

# 25. 简历 Bullet 模板

以下内容必须在真实实现后才能使用。

### Bullet 1：系统

> Built a FastAPI-based lottery service supporting campaign configuration, weighted prize selection, persistent draw orders, and MySQL-backed transactional data management.

### Bullet 2：并发

> Implemented atomic inventory control with Redis Lua, distributed rate limiting, and request idempotency to prevent overselling and duplicate awards under concurrent requests.

### Bullet 3：验证

> Developed pytest concurrency tests and Locust load benchmarks to evaluate throughput, tail latency, inventory consistency, and duplicate-order behavior under simulated concurrent traffic.

如果最终测得真实数字，可以升级为：

> Tested the draw API under `[N]` concurrent users / `[M]` total requests, achieving `[X]` RPS at `[Y] ms` P95 latency with zero oversold inventory and zero duplicate orders.

不得填写未实测数字。

---

# 26. 面试准备问题

完成项目后，自己至少能回答：

1. 为什么选择 FastAPI？
2. 为什么正式环境从 SQLite 换到 MySQL？
3. SQLAlchemy 帮你解决了什么？
4. 哪些字段建了索引？为什么？
5. 什么是事务？
6. 为什么库存扣减会超卖？
7. Redis DECR 是否已经足够？为什么还使用 Lua？
8. Redis 与 MySQL 库存不一致怎么办？
9. 什么是幂等？
10. request_id 如何设计？
11. 为什么数据库还要 UNIQUE constraint？
12. ZSet 滑动窗口如何工作？
13. Locust 测了什么？
14. P95 和平均延迟有什么区别？
15. 为什么没有拆微服务？
16. 为什么不用 Kafka / RocketMQ？
17. 如果流量扩大 10 倍，哪里最先成为瓶颈？
18. Redis 挂掉以后系统怎么办？
19. MySQL 写失败但 Redis 已经扣库存怎么办？
20. 这个项目哪些地方是你自己做的技术决策？

---

# 27. 与 City Quiz 的技术栈关系

两个项目共用：

```text
Python
FastAPI
Pydantic
SQLAlchemy
REST API
pytest
```

Lottery Engine 继续向：

```text
MySQL
Redis
Lua
Concurrency
Idempotency
Locust
```

深入。

City Quiz 继续向：

```text
PostgreSQL
pgvector
Embedding
RAG
LLM
Evaluation
Recommendation
IRT / ML
```

深入。

因此两个项目最终形成互补：

```text
                    Python Engineering
                           |
                 FastAPI / SQLAlchemy
                    /             \
                   /               \
          Lottery Engine          City Quiz
               |                      |
       Systems Engineering       AI Engineering
               |                      |
      MySQL / Redis / Lua      RAG / LLM / Eval
        Concurrency             Recommendation
```

---

# 28. 最终目标

这个项目最终不应该证明：

> “我会很多后端框架。”

而应该证明：

> **“我能够理解一个真实业务系统的正确性问题，使用 MySQL 和 Redis 做出合理设计，并通过测试和实验验证自己的实现。”**

完成这一目标后，本项目即视为成功。

不要继续为了技术栈数量无限扩张。

下一阶段的主要投入应回到：

> **City Quiz + AI/ML 能力 + 硕士申请 + AI/算法实习。**
