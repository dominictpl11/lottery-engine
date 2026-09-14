# 开发日志

按阶段记录这个项目**做了什么决策、为什么这么选、踩了什么坑、有什么实测证据**。

这份文档不是流水账。它的用途是：几个月后回头看，或者面试被问到某个设计时，
能立刻答出"当时的权衡是什么、放弃了哪个方案、凭什么证明现在这个是对的"。

每完成一个 Phase 追加一节。格式与要求见
[`docs/REQUIREMENTS.md` §11](docs/REQUIREMENTS.md)。

---

## 2026-09-14 · 重启：确立 Python 主线

`29382e8` · 4 files, +2146/-253

### 背景

仓库里并存两套实现（Java 版 2752 行 / Python 版 488 行），三份文档互相矛盾，
且都高估了进度：归档文档声称 Java "完成度 95%"。

### 做的事

把定位改成 **Python 单主线**，Java 冻结为 Legacy；重写需求规格为可验收的
FR/NFR/DDL/API 契约；建立 D1–D8 缺陷清单。

### 关键决策

**放弃"先用 Python 写完再转写成 Java"。** 这条路要把设计成本付两遍，而且转出来的
是 Python 形状的 Java，面试官一眼能看出来。真正的判断依据是两条实测：

- Java 版**从未编译成功过**。`target/` 里只有 7 个资源文件、0 个 `.class`。
- 卡了 7 个月的"8080 端口不监听"，真因在配置文件：`application.yml` 有**两个顶层
  `spring:` 键**，Spring Boot 的 YAML 加载器禁止重复键，启动直接抛
  `DuplicateKeyException`。当时写了 4 份排障文档，全在查 MySQL/Redis 是否启动，
  没人看配置结构。

**进度基线按代码核实重写。** 归档文档说 95%，实测：规则引擎整包 8 个类是死代码
（`IRuleEngine` 除自己外无任何引用）、没有订单表、`recordDrawOrder()` 是
`return true` 的空实现。对照 26 条 DoD，真正达成的约 4 条。

### 对规划的两处修正

1. **Docker Compose 从 Phase 5 提前到 Phase 1。** Phase 3 的集成/并发测试和
   Phase 4 的压测都依赖稳定可复现的 MySQL + Redis，放最后会导致反复返工。
2. **压测必须多 worker 运行。** 单进程下进程内限流器看起来"能用"，Redis 方案的
   必要性演示不出来，GIL 也会让 RPS 失真。

---

## Phase 0 · 基线整理与缺陷修复

`8f67426` · 14 files, +331/-67 · 验证 13/13

### 起点

FastAPI 服务能跑通"建活动 → 配奖品 → 抽奖 → 落库"，但 8 个缺陷里有 5 个是正确性问题。

### 修了什么

| 缺陷 | 问题 | 处理 |
| --- | --- | --- |
| D2 | `daily_limit` 被当成 60 秒窗口的次数用，每日限制**根本没实现**，用户每分钟重置配额 | 拆成两个独立规则：频率限流（秒级防刷）+ 每日配额（日级业务规则） |
| D3 | 活动库存先扣，之后无奖可发时**不回滚**，库存凭空蒸发 | 补偿路径归还库存与配额 |
| D4 | 用 naive `datetime.utcnow()` 比较 API 传入的时间，按北京时间填就被误判"不在有效期" | 确立时区约定，入参改 `AwareDatetime` |
| D6 | `status` / `award_type` 是裸 `str`，可写入任意非法值 | 绑定枚举 |
| D7 | "活动不存在"也写一行 `draw_order`，可被刷库 | 改 404 且不落库 |

### 关键决策

**改了自己刚写的规格。** 原本 FR-3 写的顺序是"每日次数 → 频率限流"，实现时发现反了：
被限流拒绝的请求不该消耗当日配额，否则高频客户端在被拒的同时把配额烧光。
限流必须在前。规格和实现一起改，并写明理由。

**naive 时间直接 422，而不是猜它的含义。** 可选的处理是"把 naive 当北京时间"或
"当 UTC"，但任何猜测都会在某类调用方身上出错。要求带偏移，让 D4 这类错误在
类型层面不可能再发生。

**时区用固定 +08:00 而不是 `zoneinfo`。** 中国 1991 年后全境单一时区、无夏令时，
固定偏移是精确的，还省掉 Windows 上必须装 `tzdata` 的依赖。

---

## Phase 1 · MySQL 化 + 容器化

`23897ff` · 25 files, +816/-197 · 验证 12/12 + Phase 0 回归 11/11

### 做的事

SQLite → MySQL 8.4；字段改名对齐规划文档；Alembic 成为 schema 唯一真源；
Docker Compose 提供 MySQL + Redis；落定事务边界；`EXPLAIN` 验证索引。

### 关键决策

**`weight` 用 `INT` 而不是 `FLOAT`。** 浮点权重会给 10 万次统计分布测试引入
无谓的精度误差，整数在后续的 Redis Lua 里也更好处理。权重不必是百分比。

**时间戳由应用写入，不用 `DEFAULT CURRENT_TIMESTAMP`。** 后者取 MySQL 服务器时区，
会让"库里都是 UTC"这条约定依赖部署环境。另外把容器钉成
`--default-time-zone=+00:00`，让手工 SQL 也落在同一口径。

**索引写了"刻意不建"的部分。** 规格要求每个索引都能回答"哪条查询需要它"；
反过来，没有查询支撑的索引就是装饰。`activity` 上没建
`(status, start_time, end_time)`，因为当前没有按状态扫描活动的查询。

### EXPLAIN 结果

先灌到 20003 行再测——几行的表上优化器必然全表扫描，测不出东西。

| 查询 | type | key |
| --- | --- | --- |
| 按 `activity_id` 取活动 | `const` | `uk_activity_id` |
| 取候选奖品 | `ref` | `idx_activity_id` |
| 每日次数统计 | `range` | `idx_user_activity_created`，**`Using index`（覆盖索引）** |

第三条是 `(user_id, activity_id, created_at)` 按"等值 → 等值 → 范围"排列的收益：
`COUNT(*)` 不需要回表。把 `created_at` 排在前面，前两个等值条件就用不上索引了。

### 踩的坑

- **`alembic.ini` 不能写中文。** Alembic 用系统 locale（本机 GBK）读它，中文注释
  直接 `UnicodeDecodeError` 起不来。
- **`ActivityResponse` 声明 `AwareDatetime` 导致 500。** 库里取出的是 naive，
  序列化时校验失败。加了 `UtcDatetime = Annotated[AwareDatetime, BeforeValidator(from_db)]`，
  对外始终带偏移、库内保持 naive。

---

## 2026-09-14 · 目录重构

`8b1d6bf` · 144 files, +152/-4780

### 触发

"Java 转 Legacy"此前只改了 README 里的一句话，目录一个文件都没动：仓库根仍是
`pom.xml` + `src/` 的 Maven 布局，主线代码埋在 `lottery_python/` 二级目录。

### 为什么必须改

GitHub Linguist 按**字节数**统计语言：Java 88KB vs Python 38KB，**这个仓库会被标成
"Java"**——与"以 Python 为主线"的定位正好相反。这是个可度量的、直接影响项目呈现的问题。

### 做的事

Python 上浮到仓库根，Java 收进 `legacy/java/`，删除 35 个文件的历史归档；
新增 `.gitattributes` 把 `legacy/**` 标为 `linguist-vendored`。语言统计中
Python 占比变为 100%。102 个文件被 git 识别为 rename，历史保留。

### 踩的坑

**`requirements.txt` 也不能写中文。** 新建 venv 时 `pip install -r` 直接
`UnicodeDecodeError`——pip 用系统 locale 解码 requirements 文件。之前能装上纯属侥幸：
那个 venv 恰好先升级过 pip，新版 pip 默认 UTF-8。与 `alembic.ini` 是同一类坑，
已写进开发约定：**被工具按 locale 读取的配置文件一律保持纯 ASCII**。

---

## Phase 2 · Redis 并发控制

`63f6c52` · 20 files, +582/-169 · 验证 21/21（单 worker）+ 8/8（4 worker）

至此 D1–D8 全部结清。

### 做的事

Redis Lua 原子扣库存、ZSet 滑动窗口限流、每日配额、`request_id` 幂等，
全部跨进程生效；删除两个进程内实现。

### 关键决策

**为什么必须用 Lua。** `GET` 判断与 `DECR` 之间存在窗口，拆成两条命令并发下必然超卖。
`DECR` 本身原子，但"判断 + 扣减"这个组合不是。Redis 单线程执行脚本，
把两步放进同一个脚本才原子。

**限流的 ZSet member 用 UUID，不用时间戳。** 旧 Java 版把时间戳同时当 score 和
member（`ZADD key now now`），同一刻的两次请求会被 ZADD 去重成一个，限流因此偏松。
这是个真 bug，新实现避开了。

**为什么用 ZSet 而不是计数器。** 固定窗口计数器在边界会放过两倍流量
（10s/3 次的配置下，第 9.9s 和第 10.1s 各放 3 次）。ZSet 以时间戳为 score，
每次先清窗口外的成员再计数，才是真滑动窗口。

**key 不存在时用 `SET NX` + MySQL 的剩余量初始化。** 用 NX 是因为并发下只能有一个
请求写初值，否则会覆盖别人已扣过的计数；用**剩余量而不是总量**，是为了 Redis 被
清空后从当前进度续上，而不是把库存凭空恢复。这条专门写了测试。

**Redis 挂了选择快速失败，没做降级开关。** 静默降级到进程内实现在多 worker 下
直接导致超卖。抽奖返回 503，健康检查不受影响，Redis 恢复后无需重启。
**拒绝服务可恢复，超发出去的奖品不可回收。**

### 实测证据

| 场景 | 结果 |
| --- | --- |
| 库存 100 / 800 并发 / **4 个 worker 进程** | **恰好 100 次中奖，零超卖**；MySQL 与 Redis 库存均归零不为负 |
| 同一 `request_id` 并发 20 次 | 库中**只有 1 条订单**，库存只扣 1 |
| 同一用户 12 次并发 | 只放行 3 次（配置 10s/3 次）。进程内实现在 4 worker 下会放行 12 次 |
| Redis 宕机 | 抽奖 503，健康检查 200，恢复后无需重启 |
| Redis key 被删 | 按 MySQL 剩余量续上（7 → 6），不是重置回总量 |

### 踩的坑

**测试客户端自己成了瓶颈。** 第一次跑 4 worker 并发测试，800 个请求有 777 个失败——
但那是**客户端**的问题：800 条线程同时建连把 Windows 临时端口打爆了（TIME_WAIT）。
应用侧库存仍然归零、无超卖。改成 keep-alive + 有界并发（40）后全绿。

这个教训对 Phase 4 的 Locust 压测直接相关：**压测跑不出数字时，先确认瓶颈不在
压测客户端自己身上**，否则会把客户端的极限误报成服务端的极限。
