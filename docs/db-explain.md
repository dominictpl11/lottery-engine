# 索引验证（EXPLAIN）

对应 `lottery_python/REQUIREMENTS.md` §4.3 与 §8.2 的验收项：每个索引都要能回答
"哪条查询需要它"，并用 `EXPLAIN` 证明真的命中。

## 测试条件

- MySQL 8.4.11（`docker compose` 起的 `lottery-mysql`）
- `activity` 20 行 / `award` 120 行 / `draw_order` **20003 行**
- 执行前跑过 `ANALYZE TABLE`，让优化器拿到新的统计信息

> 数据量是必要的：在只有几行的表上，优化器一定选全表扫描，测不出索引有没有用。

## 结果

三条查询全部命中预期索引，无全表扫描（`type` 均不为 `ALL`）。

### Q1 抽奖主链路第一步：按业务键取活动

```sql
SELECT id, activity_id, status, stock_surplus FROM activity WHERE activity_id = 930005;
```

| type | key | rows | filtered | Extra |
| --- | --- | --- | --- | --- |
| `const` | `uk_activity_id` | 1 | 100% | — |

`const` 是最好的情况：唯一索引上的等值匹配，优化器在准备阶段就把它折叠成常量。

### Q2 取候选奖品

```sql
SELECT award_id, name, weight FROM award WHERE activity_id = 930005 AND stock_surplus > 0;
```

| type | key | rows | filtered | Extra |
| --- | --- | --- | --- | --- |
| `ref` | `idx_activity_id` | 6 | 33.33% | `Using where` |

`activity_id` 走索引定位到 6 行，`stock_surplus > 0` 作为回表后的过滤条件。
奖品数量天然很小（每活动个位数），没必要为 `stock_surplus` 再建组合索引。

### Q3 每日参与次数的 DB 兜底统计

```sql
SELECT COUNT(*) FROM draw_order
WHERE user_id = 'user_100' AND activity_id = 930005 AND created_at >= '2026-09-01 00:00:00';
```

| type | key | rows | filtered | Extra |
| --- | --- | --- | --- | --- |
| `range` | `idx_user_activity_created` | 1 | 100% | `Using where; Using index` |

`Using index` 说明这是**覆盖索引**——三个条件列都在索引里，`COUNT(*)` 不需要回表。
这正是 `(user_id, activity_id, created_at)` 按「等值 → 等值 → 范围」排列的收益：
前两列定位，第三列做范围扫描。若把 `created_at` 排在前面，前两个等值条件就用不上索引了。

## 复现

```bash
cd lottery_python
docker compose up -d
./.venv/Scripts/python.exe -m alembic upgrade head
# 灌数据并执行 EXPLAIN
```
