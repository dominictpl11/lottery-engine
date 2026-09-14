const ACTIVITY_ID = 100001;

const $ = (id) => document.getElementById(id);
const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2) + Date.now());
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const SPIN_MS = 4200;

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

// 奖品类型到图标。纯展示用，后端不关心。
const EMOJI = { physical: "📱", coupon: "🎟️", virtual: "💎", none: "🙏" };

// ---------- 转盘 ----------

let awards = [];
let segments = [];
let rotation = 0;   // 累计旋转角，只增不减，保证永远正向转

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
  const size = canvas.clientWidth || 300;
  canvas.width = size * dpr;
  canvas.height = size * dpr;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, size, size);

  const cx = size / 2, cy = size / 2, r = size / 2;
  const rad = (d) => (d * Math.PI) / 180;

  segments.forEach((seg, i) => {
    const soldOut = seg.award.stock_surplus === 0;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r, rad(seg.start), rad(seg.end));
    ctx.closePath();
    // 红金交替，是国内抽奖转盘的通用视觉语言
    ctx.fillStyle = soldOut ? "#e6e0d8" : (i % 2 === 0 ? "#fff6dc" : "#ffe2ae");
    ctx.fill();
    ctx.strokeStyle = "rgba(245,166,35,.55)";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // 文字沿半径方向排，但**居中于扇区**而不是贴边——大扇区（"谢谢参与" 占 70%）
    // 贴边会把字挤到圆周上，几乎读不出来。
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(rad(seg.mid));
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const span = seg.end - seg.start;
    const big = span >= 40;              // 大扇区给更大的字和更靠内的位置
    const small = span < 16;
    let tx = big ? r * 0.58 : r - 42;    // 文字中心离圆心的距离

    // 扇区中心角落在 90°~270° 时，跟随旋转后的文字会上下颠倒。
    // 再转 180° 并把文字放到反方向，就能始终保持正着读。
    const mid = ((seg.mid % 360) + 360) % 360;
    if (mid > 90 && mid < 270) {
      ctx.rotate(Math.PI);
      tx = -tx;
    }

    ctx.fillStyle = soldOut ? "#a79f94" : "#c0392b";
    ctx.font = `700 ${small ? 10 : big ? 15 : 12.5}px system-ui, "Microsoft YaHei", sans-serif`;
    let name = seg.award.name;
    const maxLen = small ? 5 : 8;
    if (name.length > maxLen) name = name.slice(0, maxLen - 1) + "…";
    ctx.fillText(name, tx, big ? 11 : 0);

    ctx.font = `${small ? 13 : big ? 24 : 16}px serif`;
    ctx.fillText(EMOJI[seg.award.award_type] || "🎁", tx, big ? -14 : (small ? -13 : -16));
    ctx.restore();
  });
}

function buildLights() {
  const box = $("lights");
  const n = 18;
  box.innerHTML = Array.from({ length: n }, (_, i) => {
    const a = (i / n) * 2 * Math.PI - Math.PI / 2;
    const x = 50 + 48.5 * Math.cos(a);
    const y = 50 + 48.5 * Math.sin(a);
    return `<i style="left:${x}%;top:${y}%;animation-delay:${(i % 6) * 0.18}s"></i>`;
  }).join("");
}

/**
 * 把转盘转到指定奖品所在扇区。
 *
 * 结果由**后端**决定，前端只负责让指针停在对应扇区上——绝不能在前端再随机一次，
 * 那样转盘显示的结果就和真实落库的订单对不上了。
 */
function spinTo(awardId) {
  const seg = segments.find((s) => s.award.award_id === awardId);
  const canvas = $("wheel");
  if (!seg) {
    rotation += 360 * 4;
    canvas.style.transform = `rotate(${rotation}deg)`;
    return;
  }
  // 指针固定在正上方（270°）。扇区中心角 mid 旋转 R 后应落到 270°：mid + R ≡ 270
  const jitter = (Math.random() - 0.5) * (seg.end - seg.start) * 0.6;
  const target = 270 - (seg.mid + jitter);
  const turns = 5 + Math.floor(Math.random() * 2);
  rotation += turns * 360 + (((target - (rotation % 360)) % 360) + 360) % 360;
  canvas.style.transform = `rotate(${rotation}deg)`;
}

// ---------- 中奖播报 ----------
// 只播真实发生过的抽奖（本页面这次会话里的），不编造。

const feed = [];
let feedIdx = 0;

function pushFeed(userId, prizeName) {
  const masked = userId.length > 6 ? userId.slice(0, 3) + "***" + userId.slice(-2) : userId + "***";
  feed.push(`<b>${escapeHtml(masked)}</b> 抽中了 ${escapeHtml(prizeName)}`);
  if (feed.length > 30) feed.shift();
  renderFeed();
}

function renderFeed() {
  const track = $("marquee");
  if (!feed.length) {
    track.innerHTML = `<div class="marquee-item">还没有人抽奖，来做第一个</div>`;
    return;
  }
  const items = feed.slice(-8);
  track.innerHTML = items.map((t) => `<div class="marquee-item">${t}</div>`).join("");
  feedIdx = 0;
  track.style.transform = "translateY(0)";
}

setInterval(() => {
  const track = $("marquee");
  const n = track.children.length;
  if (n <= 1) return;
  feedIdx = (feedIdx + 1) % n;
  track.style.transform = `translateY(-${feedIdx * 30}px)`;
}, 2600);

// ---------- 活动与奖品 ----------

let dailyLimit = 0;
let usedToday = 0;   // 本会话内该用户已成功参与次数，仅用于界面提示

async function loadActivity() {
  const [act, aw] = await Promise.all([
    api("GET", `/api/activities/${ACTIVITY_ID}`),
    api("GET", `/api/activities/${ACTIVITY_ID}/awards`),
  ]);

  if (act.status === 404) {
    $("activity-sub").textContent = `活动 ${ACTIVITY_ID} 不存在，需要先创建`;
    $("spin-btn").disabled = true;
    return;
  }
  const a = act.data;
  dailyLimit = a.daily_limit;
  $("activity-name").textContent = a.name;
  $("activity-sub").innerHTML =
    `剩余奖池 <b>${a.stock_surplus}</b> / ${a.stock_total} · 每人每日 ${a.daily_limit} 次`;
  $("left-count").textContent = Math.max(dailyLimit - usedToday, 0);

  awards = aw.data || [];
  segments = buildSegments(awards);
  drawWheel();

  const total = awards.reduce((s, w) => s + w.weight, 0) || 1;
  $("prizes").innerHTML = awards.map((w) => `
    <div class="prize ${w.stock_surplus === 0 ? "sold-out" : ""}">
      <div class="rate">${((w.weight / total) * 100).toFixed(1)}%</div>
      <div class="emoji">${EMOJI[w.award_type] || "🎁"}</div>
      <div class="name">${escapeHtml(w.name)}</div>
      <div class="meta">剩 ${w.stock_surplus} / ${w.stock_total}</div>
    </div>`).join("");
}

// ---------- 弹窗 ----------

function showModal({ icon, title, prize, note, variant, button }) {
  $("modal-icon").textContent = icon;
  $("modal-title").textContent = title;
  $("modal-prize").textContent = prize || "";
  $("modal-note").textContent = note || "";
  $("modal-card").className = "modal-card" + (variant ? " " + variant : "");
  $("modal-close").textContent = button || "知道了";
  $("modal").hidden = false;
}
$("modal-close").onclick = () => { $("modal").hidden = true; };
$("modal").onclick = (e) => { if (e.target === $("modal")) $("modal").hidden = true; };

// ---------- 抽奖 ----------

$("new-user").onclick = () => {
  $("user-id").value = "u_" + uuid().slice(0, 8);
  usedToday = 0;
  $("left-count").textContent = dailyLimit;
};

$("spin-btn").onclick = async () => {
  const btn = $("spin-btn");
  btn.disabled = true;
  $("spin-note").textContent = "抽奖中";

  const payload = {
    request_id: uuid(),
    user_id: $("user-id").value.trim() || "demo_user",
    activity_id: ACTIVITY_ID,
  };
  const { status, data } = await api("POST", "/api/lottery/draw", payload);
  $("draw-raw").textContent =
    "POST /api/lottery/draw\n" + JSON.stringify(payload, null, 2) +
    `\n\n<- HTTP ${status}\n` + JSON.stringify(data, null, 2);

  // 被拒绝就不转：转完 4 秒再说"你被限流了"很莫名其妙。
  if (status !== 200 || data.draw_state === "rejected") {
    showReject(status, data);
    btn.disabled = false;
    $("spin-note").textContent = "立即抽";
    return;
  }

  usedToday += 1;
  $("left-count").textContent = Math.max(dailyLimit - usedToday, 0);

  const won = data.draw_state === "won";
  const landing = won ? data.award.award_id : idOfThanks();
  spinTo(landing);
  await sleep(SPIN_MS);

  if (won) {
    pushFeed(payload.user_id, data.award.award_name);
    showModal({
      icon: "🎉", title: "恭喜获得", prize: data.award.award_name,
      note: `订单 ${data.order_id.slice(0, 12)}…`, button: "开心收下",
    });
  } else {
    showModal({
      icon: "🙏", title: "谢谢参与", prize: "下次再来试试",
      note: `订单 ${data.order_id.slice(0, 12)}…`, variant: "miss", button: "再来一次",
    });
  }

  await loadActivity();
  btn.disabled = false;
  $("spin-note").textContent = "立即抽";
};

/** missed 时后端不返回 award 对象，落在"谢谢参与"扇区上。 */
function idOfThanks() {
  const none = awards.find((w) => w.award_type === "none");
  return none ? none.award_id : (awards[0] && awards[0].award_id);
}

const REJECT_TEXT = {
  rate_limited: ["⏳", "手速太快啦", "歇一会儿再来"],
  daily_limit_exceeded: ["📅", "今日次数已用完", "明天再来"],
  activity_stock_exhausted: ["📦", "奖池已空", "活动太火爆了"],
  award_stock_exhausted: ["📦", "奖品被抢光了", "活动太火爆了"],
  activity_not_running: ["🚧", "活动未开始", "请留意开始时间"],
  activity_not_in_window: ["🕐", "不在活动时间内", "请留意活动时段"],
};

function showReject(status, d) {
  if (status === 409) {
    return showModal({ icon: "⏱️", title: "请勿重复提交", prize: "上一次还在处理中",
                       variant: "reject" });
  }
  if (status === 404) {
    return showModal({ icon: "❓", title: "活动不存在", variant: "reject" });
  }
  if (status >= 500) {
    return showModal({ icon: "⚠️", title: status === 503 ? "服务繁忙" : "系统错误",
                       prize: (d && d.detail) || "", variant: "reject" });
  }
  const [icon, title, note] = REJECT_TEXT[d.reject_reason] || ["😅", d.message, ""];
  showModal({ icon, title, prize: note, note: d.reject_reason, variant: "reject" });
}

// ---------- 并发测试（开发者面板） ----------

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

buildLights();
renderFeed();
loadActivity();
