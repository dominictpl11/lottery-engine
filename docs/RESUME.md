# 简历口径

按 [`REQUIREMENTS.md` §11](REQUIREMENTS.md) 与 [`PROJECT_PLAN.md` §24–25](PROJECT_PLAN.md)。

**本文件里的每个数字都出自 [`benchmark.md`](benchmark.md) 或 pytest 的实测结果。
未实测的数字不得写入简历。**

---

## 项目名

> **Lottery Engine — Concurrency-safe Marketing Lottery Service**

"High-Concurrency" 这个说法现在可以用了——已完成 500 并发的真实压测，
但配套的限定条件（单机、组件互相争抢 CPU）必须一起说，不能只报数字。

## 技术栈

只写真实用到的：

```text
Python, FastAPI, SQLAlchemy, Alembic, MySQL, Redis, Redis Lua,
pytest, Locust, Docker Compose
```

**不能写**（项目里没有）：Celery、RabbitMQ、Kafka、Kubernetes、微服务、Elasticsearch。

## Bullet（英文）

### 1 · 系统

> Built a FastAPI lottery service with campaign/prize configuration, weighted prize
> selection, and MySQL-backed transactional order persistence; schema managed through
> Alembic migrations with unique constraints, foreign keys, CHECK constraints, and
> query-driven indexes verified via EXPLAIN.

### 2 · 并发

> Implemented atomic inventory control with Redis Lua scripts, ZSet sliding-window rate
> limiting, and request-level idempotency backed by a database unique constraint,
> preventing overselling and duplicate awards across multiple worker processes.

### 3 · 验证

> Developed 76 pytest cases across unit, integration, and concurrency layers, plus a
> Locust benchmark harness that verifies invariants directly against the database after
> each run.

### 4 · 实测数字

> Load-tested the draw API at 50/200/500 concurrent users on a 4-worker deployment,
> sustaining 146 RPS at 1.8s P95 with zero failures at 200 concurrency, and **zero
> oversold inventory and zero duplicate orders across all scenarios**.

### 5 · 性能分析（可选，体现深度）

> Diagnosed a connection-pool exhaustion bottleneck from tail-latency signatures
> (`QueuePool timeout` at exactly the 30s default), and established through controlled
> tuning that the remaining limit was CPU rather than pool size — doubling the pool
> yielded only a 21% reduction in failures.

## 中文版

- 基于 FastAPI 构建营销抽奖服务，支持活动与奖品配置、加权随机抽奖、订单持久化；
  使用 Alembic 管理 schema，索引按真实查询设计并用 EXPLAIN 验证命中情况。
- 使用 Redis Lua 实现原子库存扣减、ZSet 滑动窗口限流与请求幂等，配合数据库唯一约束
  作为最后防线，在多进程部署下杜绝超卖与重复发奖。
- 编写 76 个 pytest 用例（单元 / 集成 / 并发三层），并实现 Locust 压测编排脚本，
  每轮压测后直接查库验证不变量。
- 在 4 worker 部署下完成 50/200/500 并发压测：200 并发时 146 RPS、P95 1.8 秒、零失败；
  **四档场景全部实现零超卖、零重复订单**。
- 通过尾延迟特征定位到数据库连接池耗尽，并用对照实验证明进一步的瓶颈是 CPU 而非连接池
  （连接池翻倍仅带来 21% 的失败下降）。

## 面试时要能答出来的

这些在 [`DEVLOG.md`](../DEVLOG.md) 和 README 里都有对应段落：

| 问题 | 落点 |
| --- | --- |
| Redis DECR 已经原子了，为什么还要 Lua？ | README §7：原子的是 DECR，不是"判断 + 扣减"这个组合 |
| 为什么用 ZSet 而不是计数器限流？ | README §9：固定窗口在边界会放过两倍流量 |
| Redis 挂了怎么办？ | README §7：快速失败返回 503。拒绝服务可恢复，超发的奖品不可回收 |
| MySQL 写失败但 Redis 已扣库存？ | README §5 + DEVLOG Phase 3：显式补偿，且有注入失败的测试覆盖 |
| 为什么数据库还要 UNIQUE？ | README §8：Redis 幂等失效时的最后一道防线 |
| 哪些字段建了索引？为什么？ | README §6：每个索引对应一条真实查询；也说明了哪些**刻意不建** |
| 流量扩大 10 倍，哪里先成为瓶颈？ | README §12：先是连接池，修完之后是 CPU——有对照实验数据 |
| 为什么不拆微服务 / 不用 Kafka？ | README §3、PROJECT_PLAN §3.3：当前规模下只增加解释成本 |
| 为什么从 Java 换到 Python？ | README 末尾：Java 版从未编译成功，卡点是 YAML 重复键 |

## 不能说的

- 不能说"支持高并发"而不给数字和测试条件。
- 不能把 benchmark 的 RPS 说成架构上限——那是单台笔记本的总容量。
- 不能写异步发奖、消息队列：尚未实现，订单停在 `award_state = pending`。
