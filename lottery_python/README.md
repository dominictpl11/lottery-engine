# Python 版抽奖引擎

这是与 Java 版并列维护的 FastAPI 实现，默认使用 SQLite，目标是先跑通核心业务链路，
再逐步补充 Redis 原子扣库存、异步发奖、规则引擎、压测和自动化测试。

## 环境

- Python 3.11+
- 依赖列表：`requirements.txt`
- 默认数据库：`lottery.db`（首次启动自动创建，已加入忽略规则）
- 默认端口：`8000`

## 启动

在项目根目录运行：

```powershell
cd lottery_python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

如果不使用 PowerShell，请使用当前终端对应的虚拟环境激活命令。

访问：

- 健康检查：`http://127.0.0.1:8000/api/health`
- Swagger：`http://127.0.0.1:8000/docs`

## 当前接口

- `POST /api/activities`：创建活动
- `POST /api/activities/{activity_id}/awards`：配置奖品
- `POST /api/lottery/draw`：执行抽奖
- `GET /api/health`：健康检查

抽奖请求示例：

```json
{
  "user_id": "user001",
  "activity_id": 100001
}
```

## 当前功能

- 活动和奖品配置
- 加权随机抽奖
- 抽奖订单落库
- 进程内库存扣减和用户限流
- 可选 Redis 配置入口

详细需求、阶段目标和验收标准见 [`REQUIREMENTS.md`](REQUIREMENTS.md)。

本地虚拟环境、SQLite 数据库和 Python 缓存均为可重建内容，不应提交到版本库。
