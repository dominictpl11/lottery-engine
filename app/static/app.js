const ACTIVITY_ID = 100001;

const $ = (id) => document.getElementById(id);
const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2) + Date.now());

async function api(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch (_) { /* 无响应体 */ }
  return { status: res.status, data };
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

// ---------- 转盘 ----------

const SEG_COLORS = ["#4f8cff", "#8957e5", "#3fb950", "#d29922", "#db6d28", "#1f6feb", "#a371f7"];
const MUTED_COLOR = "#2d333b";

let awards = [];      // 后端返回的奖品，顺序即转盘扇区顺序
let segments = [];    // { award, start, end, mid }  角度制，0 = 3 点钟方向，顺时针
let rotation = 0;     // 转盘当前累计旋转角度（只增不减，保证永远正向转）

function buildSegments(list) {
  const total = list.reduce((s, w) => s + w.weight, 0) || 1;
  let cursor = 0;
  return list.map((w) => {
    const span = (w.weight / total) * 360;
    const seg = { award: w, start: cursor, end: cursor + span, mid: cursor + span / 2 };
    cursor += span;
    return seg;
  });
}

function drawWheel() {
  const canvas = $("wheel");
  const dpr = window.devicePixelRatio || 1;
  const size = canvas.clientWidth || 360;
  canvas.width = size * dpr;
  canvas.height = size * dpr;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, size, size);

  const cx = size / 2, cy = size / 2, r = size / 2 - 4;
  const rad = (deg) => (deg * Math.PI) / 180;

  segments.forEach((seg, i) => {
    const soldOut = seg.award.stock_surplus === 0;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r, rad(seg.start), rad(seg.end));
    ctx.closePath();
    ctx.fillStyle = soldOut ? MUTED_COLOR
      : seg.award.award_type === "none" ? "#30363d"
      : SEG_COLORS[i % SEG_COLORS.length];
    ctx.fill();
    ctx.strokeStyle = "#0d0f13";
    ctx.lineWidth = 2;
    ctx.stroke();

    // 扇区文字：沿半径方向排布
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(rad(seg.mid));
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillStyle = soldOut ? "#6b7280" : "#fff";
    const span = seg.end - seg.start;
    ctx.font = `${span < 18 ? 11 : 13}px system-ui, "Microsoft YaHei", sans-serif`;
    let name = seg.award.name;
    const maxLen = span < 18 ? 5 : 8;
    if (name.length > maxLen) name = name.slice(0, maxLen - 1) + "…";
    ctx.fillText(name, r - 14, 0);
    ctx.restore();
  });
}

/**
 * 把转盘转到指定奖品所在的扇区。
 *
 * 关键：结果由**后端**决定，前端只负责让指针停在对应扇区上——
 * 绝不能在前端随机再挑一个奖品，那样转盘和真实订单就对不上了。
 */
function spinTo(awardId) {
  const seg = segments.find((s) => s.award.award_id === awardId);
  const canvas = $("wheel");
  if (!seg) {           // 理论上不该发生；兜底转几圈就停
    rotation += 360 * 4;
    canvas.style.transform = `rotate(${rotation}deg)`;
    return;
  }
  // 指针固定在正上方（270°）。扇区中心角 mid 旋转 R 后应落到 270°：
  //     mid + R ≡ 270  (mod 360)
  // 再叠加若干整圈，并在扇区内加一点随机偏移，避免每次都精确停在正中。
  const jitter = (Math.random() - 0.5) * (seg.end - seg.start) * 0.6;
  const target = 270 - (seg.mid + jitter);
  const turns = 5 + Math.floor(Math.random() * 2);
  const next = rotation + turns * 360 + ((target - (rotation % 360)) % 360 + 360) % 360;
  rotation = next;
  canvas.style.transform = `rotate(${rotation}deg)`;
}

const SPIN_MS = 4000;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---------- 活动与奖品 ----------

async function loadActivity() {
  const [act, aw] = await Promise.all([
    api("GET", `/api/activities/${ACTIVITY_ID}`),
    api("GET", `/api/activities/${ACTIVITY_ID}/awards`),
  ]);

  if (act.status === 404) {
    $("activity-info").innerHTML =
      `<span class="tag error">活动不存在</span> 需要先创建活动 ${ACTIVITY_ID}`;
    $("spin-btn").disabled = true;
    return;
  }
  const a = act.data;
  $("activity-info").innerHTML =
    `<strong>${escapeHtml(a.name)}</strong><br>` +
    `<span class="muted">活动库存 <code>${a.stock_surplus} / ${a.stock_total}</code> · ` +
    `每人每日 <code>${a.daily_limit}</code> 次 · ` +
    `<span class="tag ${a.status === "running" ? "won" : "rejected"}">${a.status}</span></span>`;

  awards = aw.data || [];
  segments = buildSegments(awards);
  drawWheel();

  const total = awards.reduce((s, w) => s + w.weight, 0) || 1;
  $("award-table").querySelector("tbody").innerHTML = awards
    .map((w) => `
      <tr class="${w.stock_surplus === 0 ? "sold-out" : ""}">
        <td>${escapeHtml(w.name)}</td>
        <td class="num">${((w.weight / total) * 100).toFixed(1)}%</td>
        <td class="num">${w.stock_surplus} / ${w.stock_total}</td>
      </tr>`)
    .join("");
}

// ---------- 单次抽奖 ----------

$("new-user").onclick = () => { $("user-id").value = "u_" + uuid().slice(0, 8); };

$("spin-btn").onclick = async () => {
  const btn = $("spin-btn");
  btn.disabled = true;
  $("draw-result").className = "result";
  $("draw-result").innerHTML = `<span class="muted">抽奖中…</span>`;

  const payload = {
    request_id: uuid(),
    user_id: $("user-id").value.trim() || "demo_user",
    activity_id: ACTIVITY_ID,
  };
  const { status, data } = await api("POST", "/api/lottery/draw", payload);
  $("draw-raw").textContent =
    "POST /api/lottery/draw\n" + JSON.stringify(payload, null, 2) +
    `\n\n<- HTTP ${status}\n` + JSON.stringify(data, null, 2);

  // 被拒绝（限流 / 配额 / 无库存）就不转——转完再说"你被限流了"很莫名其妙。
  const rejected = status !== 200 || data.draw_state === "rejected";
  if (rejected) {
    renderDraw(status, data, true);
    btn.disabled = false;
    return;
  }

  // 中奖和未中奖都会落在某个真实扇区上（"谢谢参与"也是一个奖品）。
  spinTo(data.award ? data.award.award_id : awardIdOfMissed(data));
  await sleep(SPIN_MS);
  renderDraw(status, data, false);
  await loadActivity();
  btn.disabled = false;
};

/** missed 时后端不返回 award 对象，从订单里拿不到奖品 ID，退而求其次找"谢谢参与"扇区。 */
function awardIdOfMissed(_data) {
  const none = awards.find((w) => w.award_type === "none");
  return none ? none.award_id : (awards[0] && awards[0].award_id);
}

function renderDraw(status, d, shake) {
  const box = $("draw-result");
  const cls = (s) => { box.className = "result " + s + (shake ? " shake" : ""); };

  if (status >= 500) {
    cls("error");
    box.innerHTML = `<span class="tag error">HTTP ${status}</span>
      <span class="big">${escapeHtml((d && d.detail) || "系统错误")}</span>`;
    return;
  }
  if (status === 404) {
    cls("error");
    box.innerHTML = `<span class="tag error">404</span><span class="big">活动不存在</span>`;
    return;
  }
  if (status === 409) {
    cls("rejected");
    box.innerHTML = `<span class="tag rejected">409</span>
      <span class="big">同一 request_id 正在处理中</span>`;
    return;
  }

  const state = d.draw_state;
  cls(state);
  if (state === "won") {
    box.innerHTML = `<span class="tag won">won</span>
      <span class="big">🎉 ${escapeHtml(d.award.award_name)}</span>
      <span class="muted">order <code>${d.order_id.slice(0, 10)}…</code></span>`;
  } else if (state === "missed") {
    box.innerHTML = `<span class="tag missed">missed</span>
      <span class="big">谢谢参与</span>
      <span class="muted">order <code>${d.order_id.slice(0, 10)}…</code></span>`;
  } else {
    box.innerHTML = `<span class="tag rejected">rejected</span>
      <span class="big">${escapeHtml(d.message)}</span>
      <code>${d.reject_reason}</code>`;
  }
}

// ---------- 并发测试 ----------

$("burst-btn").onclick = async () => {
  const btn = $("burst-btn");
  const n = Math.max(1, Math.min(500, parseInt($("burst-n").value, 10) || 100));
  const sameUser = $("burst-same-user").checked;
  const sameReq = $("burst-same-req").checked;

  btn.disabled = true;
  $("burst-result").innerHTML = `<p class="muted">正在并发打出 ${n} 个请求…</p>`;

  const before = (await api("GET", `/api/activities/${ACTIVITY_ID}`)).data;
  const fixedReq = uuid();
  const t0 = performance.now();
  const results = await Promise.all(
    Array.from({ length: n }, () =>
      api("POST", "/api/lottery/draw", {
        request_id: sameReq ? fixedReq : uuid(),
        user_id: sameUser ? "burst_shared_user" : `burst_${uuid().slice(0, 8)}`,
        activity_id: ACTIVITY_ID,
      }).catch(() => ({ status: 0, data: null }))
    )
  );
  const elapsed = performance.now() - t0;
  const after = (await api("GET", `/api/activities/${ACTIVITY_ID}`)).data;

  renderBurst(results, before, after, elapsed, n, sameReq);
  await loadActivity();
  btn.disabled = false;
};

function renderBurst(results, before, after, elapsed, n, sameReq) {
  const tally = {};
  const orderIds = new Set();
  for (const { status, data } of results) {
    let key;
    if (status === 0) key = "连接失败";
    else if (status >= 500) key = `HTTP ${status}（系统错误）`;
    else if (status === 409) key = "409 处理中";
    else if (status === 404) key = "404";
    else if (data.draw_state === "won") { key = "中奖"; orderIds.add(data.order_id); }
    else if (data.draw_state === "missed") { key = "未中奖"; orderIds.add(data.order_id); }
    else { key = "拒绝 · " + data.reject_reason; }
    tally[key] = (tally[key] || 0) + 1;
  }

  // 用**去重后的订单数**而不是成功响应数。
  // 同一 request_id 的重复请求拿到的是回放结果，order_id 相同——它们不是新的抽奖，
  // 不该计入消耗。按响应数算的话，幂等场景会误报成"不变量被破坏"。
  const drawn = orderIds.size;
  const consumed = before.stock_surplus - after.stock_surplus;
  const checks = [
    { ok: after.stock_surplus >= 0, text: `库存未被扣成负数（剩余 ${after.stock_surplus}）` },
    { ok: drawn === consumed, text: `产生的订单数 ${drawn} == 实际消耗库存 ${consumed}` },
    { ok: after.stock_surplus <= before.stock_surplus,
      text: `库存只减不增（${before.stock_surplus} -> ${after.stock_surplus}）` },
  ];
  if (sameReq) {
    checks.push({
      ok: orderIds.size <= 1 && consumed <= 1,
      text: `同一 request_id 只产生 ${orderIds.size} 个订单、只扣 ${consumed} 个库存（幂等）`,
    });
  }
  const allOk = checks.every((c) => c.ok);

  const rows = Object.entries(tally).sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `<tr><td>${escapeHtml(k)}</td><td class="num">${v}</td></tr>`).join("");

  $("burst-result").innerHTML = `
    <p class="muted">${n} 个请求，耗时 ${elapsed.toFixed(0)} ms</p>
    <table><thead><tr><th>结果</th><th>次数</th></tr></thead><tbody>${rows}</tbody></table>
    <div class="verdict ${allOk ? "" : "fail"}">
      <h3>${allOk ? "并发不变量全部成立" : "不变量被破坏"}</h3>
      <ul>${checks.map((c) =>
        `<li><span class="${c.ok ? "pass" : "fail-mark"}">${c.ok ? "✓" : "✗"}</span> ${c.text}</li>`
      ).join("")}</ul>
    </div>`;
}

loadActivity();
