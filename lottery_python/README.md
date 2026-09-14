# Lottery Engine — Python 版（主线实现）

营销抽奖服务。本目录是项目的**唯一在维护的实现**；Java 版已冻结为 Legacy。

- 规划与阶段排期：[`docs/PROJECT_PLAN.md`](../docs/PROJECT_PLAN.md)
- 需求规格与验收标准：[`REQUIREMENTS.md`](REQUIREMENTS.md)

## 环境

- Python 3.11+
- 依赖列表：`requirements.txt`
- 当前数据库：`lottery.db`（SQLite，首次启动自动创建，已在忽略规则中）
- 目标数据库：MySQL 8（Phase 1 迁移）
- 默认端口：`8000`

## 启动

```powershell
cd lottery_python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

非 PowerShell 环境请使用当前终端对应的虚拟环境激活命令。

访问：

- 健康检查：`http://127.0.0.1:8000/api/health`
- Swagger：`http://127.0.0.1:8000/docs`

## 当前接口

- `GET  /api/health` — 健康检查
- `POST /api/activities` — 创建活动
- `POST /api/activities/{activity_id}/awards` — 配置奖品
- `POST /api/lottery/draw` — 执行抽奖

抽奖请求示例：

```json
{
  "user_id": "user001",
  "activity_id": 100001
}
```

> 目标契约（含 `request_id` 幂等键、`GET /api/activities/{activity_id}`）见
> [`REQUIREMENTS.md` §6](REQUIREMENTS.md)，尚未实现。

## 当前状态：MVP / Baseline

**可用**：活动与奖品配置、加权随机抽奖、抽奖订单落库、Swagger 文档。

**存在但实现不正确** —— 以下能力有代码，但**不满足并发正确性要求**，不要当作已完成：

| | 现状 |
| --- | --- |
| 库存扣减 | read-then-write，无原子语句/行锁，**并发下会超卖**；且活动库存在后续步骤失败时不回滚 |
| 用户限流 | 进程内 `deque` 滑动窗口，多进程失效，且内存无界增长 |
| 每日参与次数 | **未实现**。`daily_limit` 被误用为 60 秒窗口的次数，用户每分钟就会重置配额 |
| Redis | **完全未接入**。`enable_redis` / `redis_url` 是死配置，无任何代码读取 |

**完全没有**：MySQL、幂等机制、pytest、Locust 压测、Docker Compose、Alembic 迁移。

完整缺陷清单（D1–D8，含文件与行号）见 [`REQUIREMENTS.md` §9.1](REQUIREMENTS.md)。
按 [`REQUIREMENTS.md` §8](REQUIREMENTS.md) 的 Phase 划分推进。

## 约定

本地虚拟环境、SQLite 数据库、Python 缓存和 `.env` 均为可重建或敏感内容，不提交到版本库。
