# Lottery Engine

A concurrency-safe prize-draw service for marketing campaigns.
**Python 3.11 · FastAPI · MySQL 8.4 · Redis 7**

> "Lottery" here means the **prize wheel a marketing campaign runs** — configure a campaign and
> its prizes, users draw during the campaign window, the service picks a prize by weight,
> decrements stock and writes an order. It has nothing to do with predicting lottery numbers.

Running a prize draw is simple until two people click at the same moment. This project is
organised around the four things that break under concurrency, and every claim about them is
backed by a test or a benchmark you can re-run:

| What goes wrong | How it is prevented | Verified by |
| --- | --- | --- |
| **Overselling** — stock decremented more times than it exists | Atomic test-and-decrement in a Redis Lua script, with a `stock_surplus > 0` guard inside the MySQL transaction as a backstop | 7 concurrency tests and 4 load scenarios, all reporting `oversold = 0` |
| **Double submits** — a user double-clicks, a client retries a timeout | `request_id` idempotency: Redis `SET NX` on the hot path, `UNIQUE (request_id)` in MySQL as the last line of defence | 40 threads sending one `request_id` produce exactly 1 order |
| **Scripted abuse** | Redis ZSet sliding window for rate, a separate counter for the daily quota | One user firing 12 concurrent requests is let through 3 times |
| **Multi-process deployment** — the three above must still hold across workers | All contended state lives in Redis; nothing is kept in process memory | Everything above is run under `uvicorn --workers 4` |

---

## Quick start

```bash
cp .env.example .env      # change API_HOST_PORT if 8000 is taken
docker compose up -d      # MySQL + Redis + API; migrations run on startup
```

| | URL | For |
| --- | --- | --- |
| Draw page | `http://127.0.0.1:8000/` | End users. A 3x3 grid draw that **deliberately exposes no win probabilities** |
| Developer page | `http://127.0.0.1:8000/dev` | Real weights, raw request/response, a concurrency harness |
| Swagger | `http://127.0.0.1:8000/docs` | API reference |
| Health | `http://127.0.0.1:8000/api/health` | Liveness |

Create a campaign first — the demo pages expect campaign id `100001`: one call to
`POST /api/activities` and one to `POST /api/activities/{id}/awards` from Swagger.

The two pages are separate on purpose. The draw page leaks nothing that could be used to infer
the odds: every prize occupies the same number of cells in the grid and no card shows a rate. The
real `weight` exists only in the backend. The developer page then lays all of it open — weights
and normalised probabilities, raw request and response bodies, and a concurrency panel that fires
N simultaneous draws and reconciles the outcome against the database. Tick *same request_id* to
watch idempotency work: 100 requests, 1 order, 1 unit of stock consumed.

<details>
<summary>Running the API from source instead, with hot reload</summary>

```bash
docker compose up -d mysql redis
python -m venv .venv && .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```
</details>

---

## Architecture

A layered monolith. Splitting this into services at its current size would add explanation cost
without solving anything.

```text
                      Client / pytest / Locust
                                |
                                v
                +-------------------------------+
                |  FastAPI (uvicorn, N workers) |
                |        interfaces/api/        |
                +---------------+---------------+
                                |
                    application/lottery_process
                    (orchestration + compensation)
                                |
            +-------------------+-------------------+
            v                   v                   v
      domain/strategy      domain/models      infrastructure/
      weighted draw        domain model       repositories + redis/
            |                                       |
            +-------------------+-------------------+
                                |
              +-----------------+-----------------+
              v                                   v
      +---------------+                   +---------------+
      |     Redis     |                   |   MySQL 8.4   |
      |   --- gate ---|                   | --- ledger ---|
      | Lua inventory |                   | activity      |
      | ZSet window   |                   | award         |
      | idempotency   |                   | draw_order    |
      +---------------+                   +---------------+
```

**Redis is the gate, MySQL is the ledger.** Redis decides whether a request may proceed — that is
what holds under load — while MySQL records the outcome in a transaction and re-checks stock as a
backstop. The two can drift if Redis is flushed, and are realigned by re-seeding Redis counters
from MySQL's *remaining* stock.

**Redis is never degraded away.** If it is unreachable, draws return `503`. Falling back to an
in-process implementation would silently oversell the moment a second worker exists: a refused
request is recoverable, a prize that has already gone out is not.

---

## How a draw executes

```text
1.  Idempotency check (request_id)  Redis SET NX; a repeat replays the first result
2.  Load campaign                   MySQL, by uk_activity_id
3.  Status / time-window check      status == running, now inside the active window
4.  Rate limit                      Redis ZSet sliding window, default 3 per 10s
5.  Daily quota                     Redis counter, resets on the Asia/Shanghai calendar day
6.  Reserve campaign stock          Redis Lua, atomic test-and-decrement
7.  Load candidate prizes           MySQL, stock_surplus > 0
8.  Weighted random draw            pure in-memory, no infrastructure involved
9.  Reserve prize stock             Redis Lua
10. Persist (one transaction)       both stock decrements and the order commit together
11. Store the idempotency result
```

Two rules the ordering encodes:

- **Step 4 must precede step 5.** Otherwise a client that is being rate-limited also burns its
  daily quota while being rejected.
- **Anything reserved is released in reverse order on failure.** If step 6 succeeded and any of
  7–10 fails, the campaign stock and the daily quota are both given back.

<details>
<summary>Why Lua, and not GET plus DECR</summary>

```text
GET stock        <- both requests read 1
if stock > 0:
    DECR stock   <- both decrement; stock becomes -1
```

`DECR` is atomic on its own, but *test-then-decrement* is not. Redis runs a script to completion
on its single thread, so putting both steps in one script makes the pair atomic.

When the key is missing it is seeded with `SET NX` from MySQL's **remaining** stock — not the
configured total — and retried once. `NX` because under concurrency only one request may write the
seed; otherwise it would clobber decrements another request has already made. Remaining rather
than total so that a flushed Redis resumes from real progress instead of resurrecting stock.
</details>

<details>
<summary>Rate limiting: two different rules that are easy to conflate</summary>

| | Purpose | Implementation | Default |
| --- | --- | --- | --- |
| Rate limit (FR-6a) | Anti-abuse, second scale | Redis ZSet sliding window + Lua | 3 per 10s |
| Daily quota (FR-6b) | Business allowance, day scale | Redis counter, date in the key | `activity.daily_limit` |

A fixed-window counter lets through double the traffic at the boundary — with 3-per-10s, three at
t=9.9s and three more at t=10.1s. The ZSet scores members by timestamp and evicts everything
outside the window before counting.

Members are UUIDs rather than timestamps: with timestamps, several requests in the same instant
collapse into a single `ZADD` and the limit silently loosens.
</details>

<details>
<summary>Schema and index design</summary>

Three tables: `activity` / `award` / `draw_order`. Full DDL in
[`docs/REQUIREMENTS.md` §4.2](docs/REQUIREMENTS.md).

Each constraint blocks a specific class of error:

| Constraint | What it stops |
| --- | --- |
| `uk_request_id` | The last line of idempotency. Even with Redis down or flushed, the database refuses the duplicate order |
| `ck_activity_stock` / `ck_award_stock` | `stock_surplus >= 0`; stock cannot go negative |
| `ck_activity_time` | `end_time > start_time` |
| `fk_award_activity` | A prize cannot belong to a campaign that does not exist |

Indexes are designed against real queries — each one answers "which query needs this?".
`EXPLAIN` output lives in [`docs/db-explain.md`](docs/db-explain.md):

| Index | Query it serves | EXPLAIN |
| --- | --- | --- |
| `uk_activity_id` | Step 2, loading the campaign by business key | `const` |
| `idx_activity_id` | Step 7, loading candidate prizes | `ref` |
| `idx_user_activity_created` | The database-side daily-count fallback | `range` + **`Using index`** |

The third is ordered equality, equality, range, so the `COUNT(*)` never touches the table. Putting
`created_at` first would make the two equality predicates unusable.

`activity` deliberately has **no** `(status, start_time, end_time)` index: nothing scans campaigns
by status, and an index no query uses is decoration.
</details>

---

## Tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
docker compose up -d
pytest                    # 83 tests
pytest -m concurrency     # concurrency only, slower
```

| Layer | Tests | Coverage |
| --- | --- | --- |
| `tests/unit/` | 16 | Draw algorithm, including a 100k-sample distribution check; time-zone handling |
| `tests/integration/` | 60 | Endpoint happy paths and edges, 8 categories of business rejection, Redis components, 5 compensation paths |
| `tests/concurrency/` | 7 | No overselling, quota not breachable, idempotency, the database uniqueness backstop |

Tests run against a separate `lottery_test` database and Redis `db 1`. `conftest.py` asserts the
target before touching anything, so pointing them at the wrong instance fails loudly instead of
wiping the development data.

Compensation paths are exercised by monkeypatching a MySQL commit failure into the flow. Those
branches almost never fire under normal traffic, which is exactly why they are the easiest to get
wrong and the hardest to notice in production.

---

## Benchmarks

```bash
python load_tests/run_benchmark.py           # all four scenarios
python load_tests/run_benchmark.py Stress    # a single scenario, for debugging
```

The harness rebuilds the data, starts the service with 4 workers, runs each Locust scenario, then
**queries the database to check the invariants** and writes [`docs/benchmark.md`](docs/benchmark.md).

Environment: one laptop, 16 logical cores, MySQL 8.4 and Redis 7 in Docker, `uvicorn --workers 4`.
**Server, database, Redis and the load generator all compete for the same CPU.**

| Scenario | Users | Requests | RPS | P50 | P95 | Failures |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline | 50 | 5384 | 90.9 | 220 ms | 1300 ms | 0.00% |
| Medium | 200 | 8671 | 146.4 | 1100 ms | 1800 ms | 0.00% |
| Stress | 500 | 7728 | 130.3 | 1400 ms | 9500 ms | 1.40% |
| Contention | 200 | 7458 | 256.3 | 440 ms | 1100 ms | 0.13% |

**All four scenarios report `oversold = 0` and `duplicate order = 0`.** Every failure in the
Stress run is a `503`, a capacity signal; there are no `500`s. The Contention scenario deliberately
squeezes 200 users against 500 units of stock for 30 seconds: exactly 500 draws succeed, the rest
take the early-rejection path, which is why its RPS is not comparable with the other three.

Two deliberate choices in the methodology:

- Each request uses a **fresh** `request_id` and `user_id`. Reusing the first hits the idempotency
  cache and reusing the second hits the rate limiter; neither measures the draw path.
- **Business rejections are not failures.** Out-of-stock and rate-limited are the system behaving
  correctly, and counting them as failures would make the failure rate useless for diagnosis.

<details>
<summary>What the load test actually found</summary>

The first run peaked at 30929 ms — **exactly SQLAlchemy's default `pool_timeout`**. The logs
confirmed it: `QueuePool limit of size 5 overflow 10 reached`. That is 15 connections per process,
60 across 4 workers, while FastAPI's synchronous endpoints run on a 40-thread pool.

Changing only the pool size:

| pool + overflow | Total across 4 workers | Stress RPS | Stress failures |
| --- | --- | --- | --- |
| 5 + 10 (default) | 60 | 49.2 | 372 |
| 20 + 10 | 120 | 73.3 | 312 |
| 40 + 20 | 240 | 108.2 | 246 |

Quadrupling the pool bought a 34% drop in failures, so the bottleneck had already moved:
connections were not scarce, they were held longer because queries ran slower on a saturated CPU.
The conclusion is that this machine saturates around 200 concurrent users — not that a larger pool
would fix it.

One semantic fix came out of the same run: pool exhaustion now returns `503` instead of `500`. The
service is not broken, it is past the load it can serve concurrently; separating the two is what
makes the failure rate diagnostic.
</details>

---

## API

| Method | Path | |
| --- | --- | --- |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/activities` | Create a campaign (201) |
| `GET` | `/api/activities/{activity_id}` | Read campaign configuration |
| `GET` | `/api/activities/{activity_id}/awards` | List prizes, including exhausted ones |
| `POST` | `/api/activities/{activity_id}/awards` | Configure a prize (201) |
| `POST` | `/api/lottery/draw` | Execute a draw |

Three contract details worth knowing before integrating:

- **`request_id` is required** — a client-generated UUID. Resending the same one produces the side
  effect exactly once; a duplicate arriving while the first is still in flight gets `409`.
- **Timestamps must carry a UTC offset**, for example `2026-09-14T18:00:00+08:00`. A naive value is
  rejected with `422` rather than guessed to be UTC. Internally: aware UTC in the application,
  naive UTC in the database, converted explicitly at the boundary.
- **`success` means the flow completed, not that the user won.** Winning and not winning are both
  `true`; only a business rejection is `false`, and it carries a `reject_reason` from a fixed set.

Full contract in [`docs/REQUIREMENTS.md` §6](docs/REQUIREMENTS.md).

---

## Project status and roadmap

The core is complete and verified. Six phases are done: baseline defect fixes, MySQL with Alembic
and Compose, Redis concurrency control, the pytest suite, Locust benchmarks, and API
containerisation.

What is planned next, in order:

1. **Asynchronous fulfilment** with Celery and Redis. Orders currently stop at
   `award_state = pending`; a worker should deliver the prize with retries and a failure record.
   This needs task-level idempotency — a retried task must not deliver twice.
2. **Move the load generator and the dependencies onto separate hosts**, to measure throughput
   that is not distorted by everything sharing one CPU.
3. **CI on GitHub Actions** for the unit and integration suites.
4. **A campaign lifecycle sweeper**: close expired campaigns, clean up the Redis keys belonging to
   campaigns that have ended.

Explicitly **not** planned: microservice decomposition, Kafka or RocketMQ, Kubernetes, service
mesh, Elasticsearch. The goal is a small system whose correctness can be demonstrated, not a large
one whose behaviour can only be asserted.

---

## Known limitations

Stating the boundary does not weaken the project; it says how far it has actually been verified.

- **Redis and MySQL are dual-written, with no distributed transaction.** Redis is the gate, MySQL
  the ledger, and failure paths use explicit compensation rather than two-phase commit. If the
  compensation itself fails the two can drift briefly; the next request re-seeds the Redis counter
  from MySQL's remaining stock.
- **The draw is unavailable when Redis is**, returning `503`. Deliberate, not an oversight — see
  the architecture section.
- **Benchmark numbers come from a single laptop** with everything competing for CPU. They are
  valid for comparing configurations against each other, not as a ceiling for the architecture.
- **Prize fulfilment is not implemented.** Orders stop at `award_state = pending`; nothing is
  wired up to a coupon or logistics system.
- **Single deployment, no HA.** No service discovery, circuit breaking or graceful degradation.
- **No accounts or authentication** — `user_id` is supplied by the caller.
- **No admin UI**; campaigns and prizes are configured through the API.

---

## Repository layout

```text
lottery-engine/
├─ app/                  application code (interfaces / application / domain / infrastructure)
├─ migrations/           Alembic migrations, the only way the schema changes
├─ tests/                unit / integration / concurrency
├─ load_tests/           locustfile and benchmark orchestration
├─ docs/                 requirements spec, benchmark report, index verification
├─ docker/               image entrypoint, MySQL init
├─ legacy/java/          frozen Java implementation, reference only
├─ Dockerfile
└─ docker-compose.yml
```

| Document | |
| --- | --- |
| [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) | Requirements spec: FR/NFR, DDL, API contract, acceptance criteria |
| [`DEVLOG.md`](DEVLOG.md) | Development log: decisions per phase, approaches rejected, bugs and their root causes |
| [`docs/benchmark.md`](docs/benchmark.md) | Benchmark report |
| [`docs/db-explain.md`](docs/db-explain.md) | `EXPLAIN` output behind the index design |

Conventions for working in this repo: the schema changes through Alembic only, never
`create_all`; secrets live in `.env` and are not committed; `requirements.txt` and `alembic.ini`
must stay pure ASCII, because pip and Alembic decode them with the system locale, which is GBK on
the development machine. Each completed phase appends a section to `DEVLOG.md` in the same commit
as its code — run `git config core.hooksPath .githooks` once after cloning to enable the check
that enforces it.

