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

## 当前状态：Phase 0 完成

**可用**：活动与奖品配置、加权随机抽奖、抽奖订单落库、Swagger 文档。

**Phase 0 已修复**（D2/D3/D4/D6/D7，详见 [`REQUIREMENTS.md` §9.1](REQUIREMENTS.md)）：

| | 修复内容 |
| --- | --- |
| 每日次数 | `daily_limit` 此前被当成 60 秒窗口用，现已拆成两个独立规则：频率限流（FR-6a，默认 10s/3 次，可配置）与每日参与次数（FR-6b，按 Asia/Shanghai 自然日重置） |
| 库存补偿 | 活动库存扣减后若无奖可发或奖品扣减失败，现会归还活动库存与当日配额；此前会凭空蒸发 |
| 时区 | 应用内统一使用 aware UTC；API 入参必须带时区偏移，naive 值返回 422，不再被静默当成 UTC |
| 枚举校验 | `state` / `award_type` 绑定枚举，非法值返回 422；`end_time <= begin_time` 返回 422 |
| 脏请求 | 活动不存在返回 404 且不再写 `draw_order`，堵掉刷库入口 |
| 响应语义 | `success` 表示流程是否正常完成而非是否中奖；业务拒绝返回 `success=false` 并带 `reject_reason` |

**仍然不正确 / 尚未实现**：

| | 现状 |
| --- | --- |
| 库存扣减（D1） | 仍是 read-then-write，**并发下会超卖**。Phase 2 用 Redis Lua 原子扣减替换 |
| 限流存储（D5） | 仍是进程内 `deque`，多进程失效。Phase 2 换成 Redis ZSet |
| Redis（D8） | **仍未接入**，`enable_redis` / `redis_url` 是占位配置 |
| 幂等 | 未实现，`request_id` 随 Phase 2 加入 |
| "谢谢参与" | 应记为 `missed`，需随 Phase 1 的 `AwardType` 改名（`text` → `none`）一并处理 |

**完全没有**：MySQL、pytest、Locust 压测、Docker Compose、Alembic 迁移。

按 [`REQUIREMENTS.md` §8](REQUIREMENTS.md) 的 Phase 划分推进，下一步是 Phase 1（MySQL 化 + 容器化）。

## 约定

本地虚拟环境、SQLite 数据库、Python 缓存和 `.env` 均为可重建或敏感内容，不提交到版本库。
