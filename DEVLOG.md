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

---

## Phase 3 · pytest 测试体系

`99339ba` · 76 个用例 · unit 16 / integration 53 / concurrency 7

### 起点

前三个阶段的验证全靠一次性脚本，跑完就扔在 scratchpad 里。这意味着：没有回归保护，
每次改动都得靠人重新想一遍"这会不会破坏之前修好的东西"。

### 关键决策

**测试跑在独立的库上。** MySQL 用 `lottery_test`，Redis 用 db index 1。
测试要 `TRUNCATE` 和 `FLUSHDB` 才能保证用例之间互不干扰，跑在开发库上迟早会误删数据。
`conftest.py` 里加了两条断言，跑错目标直接失败而不是清空开发数据：

```python
assert "lottery_test" in settings.database_url
assert r.connection_pool.connection_kwargs.get("db") == 1
```

`lottery_test` 库由 compose 的 init 脚本创建，而不是靠测试代码用 root 权限去建——
测试不应该需要 root。

**环境变量必须在导入 app 之前设好。** `settings` 是模块级单例，一旦导入就固定。
放在 `conftest.py` 顶部有效，因为 pytest 保证 conftest 先于测试模块加载。

**测试库用 `metadata.create_all` 而不是跑 Alembic。** 生产路径是迁移，但测试库每次
从零开始，两者的真源都是 `app/domain/models.py`，直接建表更快且等价。
迁移本身能否复现结构由 Phase 1 的验收保证。

**并发测试用线程池打进程内的 ASGI 应用。** 它验证的是 Redis Lua 与 MySQL 条件
UPDATE 的原子性，这两者跨进程同样成立。真正的多进程验证交给 Phase 4 的压测。

**统计测试的容差写了理由，不是拍脑袋。** 10 万次模拟、相对误差 5%：按二项分布，
p=0.01 时标准差约 0.03%，5% 足够宽松到不会偶发失败，又足够紧到能抓出"权重没生效"。

### 覆盖了什么

| 层 | 内容 |
| --- | --- |
| unit | 抽奖算法（空列表 / 零权重 / 固定种子可复现 / 分布符合权重 / 权重排序）、时区约定 |
| integration | 活动与奖品接口的正常与边界、抽奖链路的 8 类业务拒绝、Redis 四个组件的边界行为、5 条补偿路径 |
| concurrency | 库存不超卖、多奖品分别限量、每日配额在并发下不被击穿、同 `request_id` 并发只产生一条订单、DB 唯一约束兜底 |

其中多条是显式的缺陷回归保护：D2（每日配额与限流是两条规则）、D4（naive 时间被拒）、
D6（非法枚举被拒）、D7（不存在的活动不落库），以及旧 Java 版 ZSet member 用时间戳
导致限流偏松的那个 bug。

### 补偿路径怎么测的

"Redis 已扣库存但 MySQL 写入失败"在正常流量下几乎不会发生，只能注入：

```python
monkeypatch.setattr(process.db, "commit", boom)
with pytest.raises(DrawPersistenceError):
    process.draw(...)
assert int(redis_client.get(act_key)) == act_before   # 库存被归还
```

还验证了一条容易漏的：失败后幂等占位必须释放，否则一次偶发的数据库抖动会把那个
`request_id` 永久锁死。

### 顺带修的

`app/main.py` 的 `@app.on_event("startup")` 已被 FastAPI 弃用，改成 `lifespan`
异步上下文管理器。测试跑起来才注意到这个警告。

---

## Phase 4 · Locust 压测与瓶颈定位

`99339ba` · 报告见 [`docs/benchmark.md`](docs/benchmark.md)

### 起点

"支持高并发"此前只是一句没有数据支撑的话。Phase 3 的并发测试证明了**正确性**
（不超卖、不重复），但没有回答**能扛多少**。

### 关键决策

**每次请求用全新的 `request_id` 和 `user_id`。** 前者复用会命中幂等缓存，
测的就变成 Redis GET；后者复用会立刻撞上 10s/3 次的频率限流，测的就变成限流拒绝路径。
两种情况下拿到的 RPS 都很好看，但和抽奖链路没关系。

**业务拒绝不计入失败率。** 库存不足、限流是系统的正确行为，算成 failure 会让这个
指标失去诊断价值。压测里按 `reject_reason` 单独统计。

**压测必须多 worker。** 单进程下 GIL 会让 RPS 失真，而且进程内实现看起来也"能用"，
演示不出 Redis 方案的必要性。

**连接池耗尽返回 503 而不是 500。** 服务端没有出错，只是负载超过了它能同时处理的量。
分开之后失败率才有诊断价值：503 代表机器到顶，500 代表有 bug。

### 发现的真实瓶颈

第一次跑就出现 200 并发 15 次 500、500 并发 75 次，最大延迟 30929 ms。
**30 秒正好是 SQLAlchemy `pool_timeout` 的默认值**，日志坐实：

```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached,
connection timed out, timeout 30.00
```

默认每进程只有 15 条连接（5 + 10），4 worker 共 60 条，而 FastAPI 的同步端点跑在
40 线程的线程池里。做了一组只改连接池的对照：

| pool + overflow | 4 worker 合计 | Stress RPS | Stress 失败 |
| --- | --- | --- | --- |
| 5 + 10（默认） | 60 | 49.2 | 372 |
| 20 + 10 | 120 | 73.3 | 312 |
| 40 + 20 | 240 | 108.2 | 246 |

同时把 MySQL `max_connections` 从 151 提到 500，排除数据库端的假性瓶颈。

**连接池翻倍只换来 21% 的失败下降** —— 这个比例说明瓶颈已经转移：连接不是不够分，
而是每条被占用得更久（查询在饱和的 CPU 上变慢）。所有组件跑在同一台笔记本上，
CPU 才是天花板。

所以 500 并发档的结论不是"再调大点"，而是**这台机器的饱和点在 200 并发附近**。
这恰好回答了项目文档 §26 Q17："流量扩大 10 倍，哪里最先成为瓶颈" —— 先是连接池，
修完之后是 CPU。

### 踩的坑：压测工具自己出了四次问题

这一阶段绝大部分时间花在这上面，而不是被测系统。按发现顺序：

1. **`subprocess` 解码崩溃。** 默认用系统 locale（GBK）解码子进程输出，
   Locust 打印的中文直接 `UnicodeDecodeError`。与 `requirements.txt`、`alembic.ini`、
   `pytest.ini` 是同一个根因——**凡是被工具按 locale 读写的文本，都要显式指定编码**。

2. **第二轮起卡死十几分钟。** `proc.terminate()` 在 Windows 上只杀 uvicorn 父进程，
   spawn 出来的 worker 全部存活。后果不只是浪费资源：这些残留连接握着 `lottery_db`
   的元数据锁，下一轮的 `DROP DATABASE` 被无限期阻塞（实测 `Waiting for table
   metadata lock` 等了 649 秒）。改用 `taskkill /F /T` 杀进程树。

3. **8030 端口上的"幽灵监听"。** 一个已不存在的 PID 仍在该端口返回合法的
   `{"status":"ok"}`，`taskkill` 报"进程不存在"，`wmic` 里也查不到——大概率属于
   另一个 Windows 账户（和本仓库 `.git` 归属 `CodexSandboxOffline` 是同类问题）。
   它抢先应答健康检查，让编排脚本误以为自己的服务已就绪，实际请求打到了连着旧库的
   进程上，表现为建活动时莫名其妙的 500。改成**每次动态挑一个确认无人应答的端口**。

4. **失败时日志被收尾清理删掉。** `shutil.rmtree(tmp)` 把最需要看的服务端日志一起
   删了。改为写到 tmp 之外，并支持只跑单个场景，排查不用每次等 5 分钟。

### 方法上的教训

第 3 个坑之前，我对症状的判断是"启动顺序错了：先起服务再 drop 库"。这个推理本身
成立（顺序确实该改），但**我没有验证就直接改了，结果症状照旧**。

前两个坑我都拿到了确凿证据才动手——`UnicodeDecodeError` 的完整堆栈、
`Waiting for table metadata lock` 的 649 秒。第三个我跳过了取证。

教训不是"要小心"，而是具体的：**改之前先让证据把假设钉死**。这里本该做的一步很简单——
在启动自己的服务之前先探一下端口，如果已经有人应答，问题立刻就暴露了。

**压测得出的数字，可信度取决于压测工具本身是否正确。**

### 最终实测数字

四档全部满足 `oversold = 0`、`duplicate order = 0`。

| 场景 | 并发 | 请求数 | RPS | P50 | P95 | 失败率 |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline | 50 | 5384 | 90.9 | 220 ms | 1300 ms | 0.00% |
| Medium | 200 | 8671 | 146.4 | 1100 ms | 1800 ms | 0.00% |
| Stress | 500 | 7728 | 130.3 | 1400 ms | 9500 ms | 1.40% |
| Contention | 200 | 7458 | 256.3 | 440 ms | 1100 ms | 0.13% |

Stress 档的失败全部是 503（容量信号），没有一个 500。

简历口径上能用的是「**200 并发下零失败、零超卖、零重复订单**」，
而不是某个 RPS 峰值——所有组件挤在同一台笔记本上，这个数字反映的是本机总容量，
不是架构上限。报告里写明了这一点。 如果没查根因，"卡住"很容易
被误读成服务端性能问题，然后去优化一个根本没问题的地方。

---

## Phase 5 · 容器化与交付

`9d1cb14` · README 15 节 · [`docs/RESUME.md`](docs/RESUME.md)

### 起点

服务能跑、有测试、有压测数据，但**别人拿到这个仓库跑不起来**：要手动建 venv、
装依赖、跑迁移、起 uvicorn，还得自己搞清楚 MySQL 和 Redis 怎么配。

### 关键决策

**镜像用 `python:3.11-slim` 而不是 alpine。** alpine 的 musl libc 会让带 C 扩展的
轮子（这里是 `cryptography`）退化成源码编译，构建慢且容易出问题。省下的几十 MB
不值这个代价。

**迁移放在 entrypoint 里，不放在应用启动代码里。** `alembic upgrade head` 在
`exec uvicorn` 之前跑完，保证"起容器"和"建表"不是两个需要人记住先后顺序的步骤。
应用代码里仍然没有 `create_all`——schema 的真源只能有一个。

**依赖等待交给 compose 的 `depends_on: service_healthy`，不在 entrypoint 里自己轮询。**
MySQL 和 Redis 都已经有 healthcheck，重复造一遍只会多一处可能写错的地方。

**宿主机端口做成可配置**（`API_HOST_PORT`）。本机 8000 已经被另一个项目占用，
写死会让 `docker compose up` 直接失败——而这恰恰是别人接触这个项目的第一条命令。

**README 按 v2 §23 的 15 节重写。** 每一节回答一个具体问题，而不是罗列功能。
技术决策段落都写了"为什么不选另一个方案"：为什么 Lua 而不是 DECR、为什么 ZSet 而不是
计数器、为什么 Redis 挂了选择拒绝服务而不是降级。

**简历口径单独成文**（`docs/RESUME.md`），并明确列出**不能说的话**：
不能说"支持高并发"而不给测试条件、不能把单机 benchmark 的 RPS 说成架构上限、
不能写尚未实现的异步发奖。约束比模板更有用——模板照抄容易，知道哪句不能写才难。

### 验证

`docker compose down -v` 清空数据卷后，`docker compose up -d` 一条命令：
三个服务全部 healthy，迁移自动执行建出三张表，容器内端到端抽奖成功，
**重放同一 `request_id` 返回同一个 `order_id`**——幂等在容器环境同样生效。
76 个测试无回归。

### 一点方法上的延续

写 README 时又撞到 heredoc 被截断（内容太长），和 Phase 2 写 `lottery_process.py`
时同一个问题。这次没有反复试，直接拆成三段写——**已经踩过的坑，第二次应该当场认出来**。
