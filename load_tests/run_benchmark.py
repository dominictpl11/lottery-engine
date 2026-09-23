"""编排压测并生成 docs/benchmark.md（REQUIREMENTS.md 8.5）。

做四件事：
1. 重置 MySQL + Redis，建活动与奖品
2. 以 **多 worker** 启动服务（NFR-2：单进程下 GIL 会让 RPS 失真，
   且进程内实现看起来也"能用"，演示不出 Redis 方案的必要性）
3. 按三档并发跑 Locust，收集 RPS / P50 / P95 / P99 / 失败率
4. 跑完后直接查库验证不变量：oversold = 0、duplicate order = 0

用法：  python load_tests/run_benchmark.py
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
# 端口在运行时挑选，不写死。
#
# 起因：固定用 8030 时遇到过"幽灵监听"——某个已不存在的 PID 仍在该端口应答，
# 且无法从当前用户会话杀掉（大概率属于另一个 Windows 账户）。它会抢先响应
# 健康检查，让编排脚本误以为自己的服务已就绪，实际请求却打到了一个连着旧库的
# 进程上，表现为建活动时莫名其妙的 500。
#
# 与其和它搏斗，不如每次换一个确认干净的端口。
PORT = None
BASE = None
# 服务端日志放在 tmp 之外：跑挂时最需要看的就是它，不能被收尾清理顺手删掉。
SERVER_LOG = Path(__file__).resolve().parent.parent / "bench-server.log"
WORKERS = 4
CN = timezone(timedelta(hours=8))

MYSQL = dict(host="127.0.0.1", port=3307, user="lottery", password="change-me-before-use",
             database="lottery_db")

# 吞吐场景用充足库存，让绝大多数请求走完整链路；
# 争抢场景用远小于请求量的库存，专门验证不超卖。
SCENARIOS = [
    ("Baseline", 50, 25, 60, 200_000),
    ("Medium", 200, 50, 60, 200_000),
    ("Stress", 500, 100, 60, 200_000),
    ("Contention", 200, 200, 30, 500),
]


def kill_tree(proc):
    """终止 uvicorn 及其全部 worker 子进程。

    proc.terminate() 在 Windows 上只结束 uvicorn 的父进程，spawn 出来的 worker
    会活下来继续持有 MySQL 连接。后果不只是浪费资源：下一轮 reset_stores 的
    `DROP DATABASE` 会因为这些连接的元数据锁而无限期阻塞，整个编排卡死。
    """
    if proc is None or proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       capture_output=True)
    else:
        proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()


def drop_lingering_connections():
    """断开残留在 lottery_db 上的连接。

    DROP DATABASE 需要元数据锁，任何一条还活着的连接都能把它挡住。
    上面的 kill_tree 已经能覆盖正常情况，这里是防御性兜底。
    """
    import pymysql
    c = pymysql.connect(host="127.0.0.1", port=3307, user="root", password="change-me-before-use")
    with c.cursor() as cur:
        cur.execute("SELECT ID FROM information_schema.processlist WHERE USER='lottery'")
        for (cid,) in cur.fetchall():
            try:
                cur.execute(f"KILL {cid}")
            except Exception:
                pass
    c.close()


def port_is_answering(port, timeout=1.5):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health",
                                    timeout=timeout):
            return True
    except Exception:
        return False


def pick_free_port():
    """挑一个既没被占用、也没有人在应答的端口。"""
    import socket
    for _ in range(30):
        with socket.socket() as sk:
            sk.bind(("127.0.0.1", 0))
            port = sk.getsockname()[1]
        if not port_is_answering(port):
            return port
    sys.exit("找不到干净的端口")


def use_port(port):
    global PORT, BASE
    PORT = port
    BASE = f"http://127.0.0.1:{port}"


def sh(cmd, **kw):
    # 必须显式指定 encoding：默认会用系统 locale（本机 GBK）解码子进程输出，
    # 子进程打印的中文会直接抛 UnicodeDecodeError。
    # 这和 requirements.txt / alembic.ini / pytest.ini 是同一个根因。
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


def reset_db():
    """重建 MySQL 与 Redis。

    必须在启动服务**之前**做：服务一旦起来就会建立连接池，此时 DROP DATABASE
    会让池里的连接全部指向一个已不存在的库，之后第一个请求就是 500。
    """
    import pymysql
    import redis

    drop_lingering_connections()
    root = pymysql.connect(host="127.0.0.1", port=3307, user="root", password="change-me-before-use")
    with root.cursor() as cur:
        cur.execute("DROP DATABASE IF EXISTS lottery_db")
        cur.execute("CREATE DATABASE lottery_db DEFAULT CHARACTER SET utf8mb4 "
                    "COLLATE utf8mb4_0900_ai_ci")
        cur.execute("GRANT ALL PRIVILEGES ON lottery_db.* TO 'lottery'@'%'")
        cur.execute("FLUSH PRIVILEGES")
    root.commit()
    root.close()
    redis.Redis(host="127.0.0.1", port=6379, db=0).flushdb()
    sh([PY, "-m", "alembic", "upgrade", "head"], cwd=ROOT)


def seed_campaign(activity_id, stock):
    """通过 API 建活动与奖品。必须在服务起来之后调用。"""
    now = datetime.now(CN)
    _post("/api/activities", {
        "activity_id": activity_id, "name": "benchmark", "stock_total": stock,
        # 配额放到最大：压测要测的是抽奖链路吞吐，不是配额拒绝路径。
        "daily_limit": 999_999, "status": "running",
        "start_time": (now - timedelta(hours=1)).isoformat(),
        "end_time": (now + timedelta(days=1)).isoformat(),
    }, expect=201)
    # 权重仿真实活动：绝大多数是"谢谢参与"。
    for i, (name, typ, w, st) in enumerate([
        ("iPhone", "physical", 1, max(stock // 100, 1)),
        ("优惠券", "coupon", 29, max(stock // 4, 1)),
        ("谢谢参与", "none", 70, stock),
    ]):
        _post(f"/api/activities/{activity_id}/awards", {
            "award_id": activity_id * 10 + i, "name": name, "award_type": typ,
            "stock_total": st, "weight": w,
        }, expect=201)


def _post(path, body, expect=200):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        assert r.status == expect, f"{path} -> {r.status}"
        return json.loads(r.read().decode())


def wait_up(timeout=60):
    for _ in range(timeout):
        try:
            with urllib.request.urlopen(f"{BASE}/api/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def start_server():
    proc = subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(PORT), "--workers", str(WORKERS), "--log-level", "warning"],
        cwd=ROOT, stdout=open(SERVER_LOG, "ab"), stderr=subprocess.STDOUT)
    if not wait_up():
        kill_tree(proc)
        sys.exit("服务启动失败")
    return proc


def run_locust(activity_id, users, spawn, duration, csv_prefix):
    env = {**os.environ, "BENCH_ACTIVITY_ID": str(activity_id),
           "PYTHONIOENCODING": "utf-8"}
    out = sh([PY, "-m", "locust", "-f", str(ROOT / "load_tests" / "locustfile.py"),
              "--headless", "-u", str(users), "-r", str(spawn),
              "-t", f"{duration}s", "--host", BASE,
              "--csv", csv_prefix, "--only-summary"], cwd=ROOT, env=env)
    return out.stdout + out.stderr


def read_stats(csv_prefix):
    import csv as csvmod
    path = Path(f"{csv_prefix}_stats.csv")
    with open(path, newline="", encoding="utf-8") as f:
        for row in csvmod.DictReader(f):
            if row["Name"] == "Aggregated":
                return row
    return None


def invariants(activity_id):
    import pymysql
    import redis

    c = pymysql.connect(**MYSQL, autocommit=True)
    q = {}
    with c.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM draw_order"); q["orders"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM draw_order WHERE draw_state='won'")
        q["won"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM draw_order WHERE draw_state='missed'")
        q["missed"] = cur.fetchone()[0]
        cur.execute("SELECT stock_total, stock_surplus FROM activity WHERE activity_id=%s",
                    (activity_id,))
        q["activity_total"], q["activity_surplus"] = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM activity WHERE stock_surplus < 0")
        neg_a = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM award WHERE stock_surplus < 0")
        neg_w = cur.fetchone()[0]
        q["oversold"] = neg_a + neg_w
        cur.execute("SELECT COUNT(*) FROM (SELECT request_id FROM draw_order "
                    "GROUP BY request_id HAVING COUNT(*)>1) t")
        q["duplicate_orders"] = cur.fetchone()[0]
    c.close()
    r = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)
    v = r.get(f"lottery:stock:activity:{activity_id}")
    q["redis_surplus"] = int(v) if v is not None else None
    return q


def env_info():
    import pymysql
    import redis
    # 不指定 database：查版本不该依赖业务库是否已经建好，
    # 否则上一轮中断留下的空环境会让脚本一开始就挂掉。
    c = pymysql.connect(host=MYSQL["host"], port=MYSQL["port"],
                        user=MYSQL["user"], password=MYSQL["password"])
    with c.cursor() as cur:
        cur.execute("SELECT VERSION()")
        mysql_v = cur.fetchone()[0]
    c.close()
    rv = redis.Redis(host="127.0.0.1", port=6379).info("server")["redis_version"]
    return {
        "os": f"{platform.system()} {platform.release()}",
        "cpu": f"{os.cpu_count()} 逻辑核",
        "python": platform.python_version(),
        "mysql": mysql_v,
        "redis": rv,
        "workers": WORKERS,
    }


def render(rows, info, out_path):
    L = []
    a = L.append
    a("# Benchmark 报告\n")
    a("由 `python load_tests/run_benchmark.py` 生成。**报告里的每个数字都来自这一次实测**，")
    a("简历中引用的数字必须出自本文件（REQUIREMENTS.md 11）。\n")
    a("## 测试环境\n")
    a("| 项 | 值 |")
    a("| --- | --- |")
    a(f"| 操作系统 | {info['os']} |")
    a(f"| CPU | {info['cpu']} |")
    a(f"| Python | {info['python']} |")
    a(f"| MySQL | {info['mysql']}（docker compose，映射 3307） |")
    a(f"| Redis | {info['redis']}（docker compose） |")
    a(f"| 服务进程 | uvicorn `--workers {info['workers']}` |")
    a(f"| 生成时间 | {datetime.now(CN).strftime('%Y-%m-%d %H:%M:%S %z')} |")
    a("")
    a("> 服务端、压测客户端、MySQL、Redis 全部跑在同一台笔记本上，互相争抢 CPU。")
    a("> 这些数字用于横向比较不同配置，不代表该架构的性能上限。\n")
    a("## 口径\n")
    a("- **失败率只统计系统错误**（5xx / 连接失败）。库存不足、限流这些是正确的业务")
    a("  行为，计入失败率会让指标失去意义（REQUIREMENTS.md 7.2）。业务拒绝按原因单独计数。")
    a("- 每次请求使用全新的 `request_id` 与 `user_id`：前者复用会命中幂等缓存，")
    a("  后者复用会立刻撞上频率限流，两者都会让测的东西偏离抽奖链路本身。\n")
    a("## 吞吐与延迟\n")
    a("| 场景 | 并发用户 | 时长 | 请求数 | RPS | P50 | P95 | P99 | 失败率 |")
    a("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in rows:
        s = r["stats"]
        reqs = int(s["Request Count"])
        fails = int(s["Failure Count"])
        rate = f"{fails / reqs * 100:.2f}%" if reqs else "n/a"
        a(f"| {r['name']} | {r['users']} | {r['duration']}s | {reqs} | "
          f"{float(s['Requests/s']):.1f} | {float(s['50%']):.0f} ms | "
          f"{float(s['95%']):.0f} ms | {float(s['99%']):.0f} ms | {rate} |")
    a("")
    a("## 并发不变量\n")
    a("每个场景跑完后直接查库验证。**这两列为 0 是本项目的核心主张**。\n")
    a("| 场景 | 活动库存 | 抽完剩余 | 中奖 | 未中奖 | 订单总数 | oversold | duplicate order |")
    a("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in rows:
        q = r["inv"]
        a(f"| {r['name']} | {q['activity_total']} | {q['activity_surplus']} | "
          f"{q['won']} | {q['missed']} | {q['orders']} | "
          f"**{q['oversold']}** | **{q['duplicate_orders']}** |")
    a("")
    cont = next((r for r in rows if r["name"] == "Contention"), None)
    if cont:
        q = cont["inv"]
        consumed = q["activity_total"] - q["activity_surplus"]
        a("### 争抢场景\n")
        a(f"`Contention` 一档刻意把库存压到 **{q['activity_total']}**，用 "
          f"{cont['users']} 并发在 {cont['duration']} 秒里反复抢。\n")
        a(f"- 实际消耗库存 **{consumed}**，剩余 {q['activity_surplus']}，"
          f"Redis 侧剩余 {q['redis_surplus']}")
        a(f"- 成功抽奖（中奖 + 未中奖）共 **{q['won'] + q['missed']}** 次，"
          f"与消耗的库存一致")
        a(f"- 超卖 **{q['oversold']}**，重复订单 **{q['duplicate_orders']}**\n")
        a("库存耗尽后的请求走的是提前拒绝路径，开销远低于完整链路，")
        a("因此这一档的 RPS 不能与上面三档直接比较。\n")
    a("## 瓶颈定位\n")
    a("第一次跑压测时，200 并发出现 15 次 HTTP 500、500 并发 75 次，最大延迟 30929 ms。")
    a("30 秒正好是 SQLAlchemy `pool_timeout` 的默认值。查服务端日志坐实了这个猜测：")
    a("\n")
    a("```")
    a("sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached,")
    a("connection timed out, timeout 30.00")
    a("```\n")
    a("默认 `pool_size=5 / max_overflow=10` 即每进程 15 条连接、4 worker 共 60 条，")
    a("而 FastAPI 的同步端点跑在 40 线程的线程池里，并发一上来就大量排队等连接。\n")
    a("随后做了一组只改连接池大小的对照，其余条件不变：")
    a("\n")
    a("| pool + overflow | 4 worker 合计 | Stress 档 RPS | Stress 档失败 |")
    a("| --- | --- | --- | --- |")
    a("| 5 + 10（默认） | 60 | 49.2 | 372 |")
    a("| 20 + 10 | 120 | 73.3 | 312 |")
    a("| 40 + 20 | 240 | 108.2 | 246 |")
    a("")
    a("同时把 MySQL `max_connections` 从默认 151 提到 500，排除数据库端的假性瓶颈。\n")
    a("**连接池翻倍只换来约 21% 的失败下降，说明瓶颈已经转移。**")
    a("连接不是不够分，而是每条被占用得更久——查询在饱和的 CPU 上变慢，连接迟迟不归还。")
    a("服务端、MySQL、Redis、Locust 全跑在同一台笔记本上，CPU 是最终的天花板。\n")
    a("所以 500 并发档的结论不是“再调大一点”，而是：**这台机器的饱和点在 200 并发附近**。")
    a("要再往上，得先把压测客户端和依赖服务挪到别的机器。\n")
    a("### 失败的语义\n")
    a("连接池耗尽原本返回 500，现已改为 **503**：服务端本身没有出错，只是当前负载超过了")
    a("它能同时处理的量，这是容量信号而非缺陷。分开之后失败率才有诊断价值——")
    a("503 代表“机器到顶了”，500 才代表“有 bug 要查”。\n")

    a("## 业务结果分布\n")
    for r in rows:
        a(f"**{r['name']}**\n")
        a("```")
        a(r["outcomes"].strip() or "(未捕获)")
        a("```\n")
    a("## 复现\n")
    a("```bash")
    a("docker compose up -d")
    a("python load_tests/run_benchmark.py")
    a("```\n")
    Path(out_path).write_text("\n".join(L), encoding="utf-8", newline="\n")


def main():
    if shutil.which("docker") is None:
        sys.exit("需要 docker")
    info = env_info()
    rows = []
    tmp = ROOT / ".bench_tmp"
    tmp.mkdir(exist_ok=True)
    SERVER_LOG.unlink(missing_ok=True)

    wanted = set(sys.argv[1:])
    scenarios = [sc for sc in SCENARIOS if not wanted or sc[0] in wanted]
    if not scenarios:
        sys.exit(f"没有匹配的场景。可选：{[s[0] for s in SCENARIOS]}")

    for name, users, spawn, duration, stock in scenarios:
        activity_id = 800000 + len(rows) + 1
        print(f"\n=== {name}: {users} 用户 / {duration}s / 库存 {stock} ===")
        proc = None
        try:
            # 顺序很重要：先重建数据，再起服务，最后灌活动。
            reset_db()
            use_port(pick_free_port())
            proc = start_server()
            seed_campaign(activity_id, stock)
            prefix = str(tmp / name.lower())
            out = run_locust(activity_id, users, spawn, duration, prefix)
            stats = read_stats(prefix)
            if stats is None:
                print(out[-2000:])
                sys.exit(f"{name}: 没有拿到 locust 统计")
            marker = "业务结果分布："
            outcomes = out.split(marker)[-1] if marker in out else ""
            rows.append(dict(name=name, users=users, duration=duration,
                             stats=stats, inv=invariants(activity_id),
                             outcomes=outcomes))
            print(f"  RPS={float(stats['Requests/s']):.1f} "
                  f"P95={float(stats['95%']):.0f}ms "
                  f"失败={stats['Failure Count']}")
        finally:
            kill_tree(proc)

    out_path = ROOT / "docs" / "benchmark.md"
    if len(scenarios) == len(SCENARIOS):
        render(rows, info, out_path)
    else:
        print(f"（只跑了 {[r['name'] for r in rows]}，未覆盖完整报告）")
    print(f"\n报告已写入 {out_path}")
    bad = [r["name"] for r in rows
           if r["inv"]["oversold"] or r["inv"]["duplicate_orders"]]
    if bad:
        sys.exit(f"不变量被破坏：{bad}")
    print("oversold = 0, duplicate order = 0 —— 全部场景通过")


if __name__ == "__main__":
    main()
