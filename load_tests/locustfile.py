"""抽奖接口压测（REQUIREMENTS.md 8.5）。

用法（由 run_benchmark.py 编排，也可单独跑）：

    locust -f load_tests/locustfile.py --headless \
           -u 200 -r 50 -t 60s --host http://127.0.0.1:8030

两个刻意的设计：

1. **每次请求用全新的 request_id 和 user_id。**
   request_id 复用会命中幂等缓存，测的就不是抽奖链路而是 Redis GET；
   user_id 复用会立刻撞上频率限流（10s/3 次），测的就变成限流拒绝路径。
   营销活动的真实形态本来就是大量不同用户各抽几次。

2. **业务拒绝不计入失败率。**
   库存不足、限流这些是系统的正确行为。把它们算成 failure 会让失败率指标
   失去意义——见 REQUIREMENTS.md 7.2。这里按 reject_reason 单独计数。
"""

import uuid
from collections import Counter

from locust import HttpUser, between, events, task

# 压测期间使用的活动 ID，由 run_benchmark.py 在启动前创建好并通过环境变量传入。
import os

ACTIVITY_ID = int(os.environ.get("BENCH_ACTIVITY_ID", "800001"))

# 业务拒绝分类计数。Locust 自身的 stats 只区分成功/失败，这里补一层业务维度。
outcomes: Counter = Counter()


@events.test_stop.add_listener
def _report(environment, **_):
    print("\n业务结果分布：")
    for k, v in sorted(outcomes.items(), key=lambda kv: -kv[1]):
        print(f"  {k:28s} {v}")


class LotteryUser(HttpUser):
    # 真实用户不会零间隔连点。留一点思考时间，避免把客户端自己压成瓶颈。
    wait_time = between(0.05, 0.2)

    @task
    def draw(self):
        payload = {
            "request_id": uuid.uuid4().hex,
            "user_id": f"lt_{uuid.uuid4().hex[:12]}",
            "activity_id": ACTIVITY_ID,
        }
        with self.client.post("/api/lottery/draw", json=payload,
                              catch_response=True, name="/api/lottery/draw") as r:
            if r.status_code != 200:
                outcomes[f"http_{r.status_code}"] += 1
                r.failure(f"HTTP {r.status_code}")
                return

            body = r.json()
            if body.get("success"):
                outcomes[body.get("draw_state", "unknown")] += 1
            else:
                # 业务拒绝：标记为成功，因为服务端行为是正确的。
                outcomes[f"rejected:{body.get('reject_reason')}"] += 1
            r.success()
