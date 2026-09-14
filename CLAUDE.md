# Lottery Engine — 项目约定

并发安全的营销抽奖服务。Python 主线，Java 版已冻结在 `legacy/java/`，不要改动它。

## 文档权威顺序

1. [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) —— 规划：定位、Phase 排期、停止线
2. [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) —— 规格：FR/NFR、DDL、API 契约、验收标准
3. [`DEVLOG.md`](DEVLOG.md) —— 决策记录

冲突时以 1 为准。规格与实现不一致时，先判断哪边错了，改规格要写明理由。

## 完成一个 Phase 时必须做的事

**这是硬要求，不是建议。** 判定"完成"的依据是 `docs/REQUIREMENTS.md` §8 里该 Phase 的
验收清单全部勾掉，其中包含以下两条：

1. **在 `DEVLOG.md` 追加一节**，按 §10 的格式：起点 / 关键决策（含放弃的方案和判断依据）/
   踩的坑及根因 / 实测证据 / commit hash 与规模。
   - 与该 Phase 的代码**在同一次提交里**。事后补写必然失真。
   - 不写流水账。"改了哪些文件"是 git 的职责。
   - **不得写未实测的数字。**
2. 把 §8 中该 Phase 的清单项和 §9.1 中已解决的缺陷状态一并更新。

提交信息用 `feat(phase-N):` / `fix(phase-N):` 前缀。`.githooks/pre-commit` 会在
提交信息含 `phase-N` 但未改动 `DEVLOG.md` 时拒绝提交。

## 硬性技术约定

- **`requirements.txt` 与 `alembic.ini` 必须保持纯 ASCII。** pip 和 Alembic 用系统 locale
  （本机是 GBK）解码这两个文件，中文注释会导致 `UnicodeDecodeError`。已踩过两次。
- **schema 只能通过 Alembic 迁移变更**，不用 `create_all`。
- **时间**：DB 存 naive UTC，应用内用 aware UTC，边界由 `app/core/timeutil.py` 显式转换。
  API 入参必须带时区偏移，naive 值返回 422。
- **Redis 不做降级**。它承担原子库存、限流、幂等；不可用时抽奖返回 503，
  绝不回退到进程内实现（多 worker 下会直接超卖）。
- **密码只放 `.env`**，不提交；`.env.example` 只放本地占位值。

## 验证方式

改动涉及并发正确性时，必须用**多 worker**验证（`uvicorn --workers 4`）——
单进程下进程内实现看起来也"能用"，测不出问题。

压测或并发测试跑不出预期数字时，先确认瓶颈不在测试客户端自己身上
（Windows 上大量并发短连接会耗尽临时端口，表现为客户端连接失败）。
