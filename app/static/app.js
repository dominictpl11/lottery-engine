const ACTIVITY_ID = 100001;

const $ = (id) => document.getElementById(id);
const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2) + Date.now());
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

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

// ---------- 九宫格 ----------

// 3x3 布局，中间是按钮，外圈 8 格顺时针的 DOM 下标：
//   0 1 2
//   3 4 5      ->  0 -> 1 -> 2 -> 5 -> 8 -> 7 -> 6 -> 3 -> 回到 0
//   6 7 8
const PERIMETER = [0, 1, 2, 5, 8, 7, 6, 3];

let awards = [];
let slots = [];        // 长度 8，slots[k] 对应 PERIMETER[k] 那一格
let activeK = 0;       // 当前高亮停在外圈的第几格

/**
 * 把奖品铺进 8 个格子。
 *
 * 刻意**平均分配**而不是按权重：如果概率高的奖品占更多格子，用户数一下格子就能
 * 反推出中奖率。真实的中奖概率只存在于后端的 weight 里，格子数不携带任何信息。
 * 4 个奖品就各占 2 格，轮流铺开，同一奖品自然分散在对角位置。
 */
function buildSlots(list, n = 8) {
  if (!list.length) return [];
  return Array.from({ length: n }, (_, i) => list[i % list.length]);
}

function renderGrid() {
  const cells = new Array(9);
  slots.forEach((award, k) => {
    const soldOut = award.stock_surplus === 0;
    cells[PERIMETER[k]] =
      `<div class="cell ${soldOut ? "sold-out" : ""}" data-k="${k}">
         <div class="emoji">${EMOJI[award.award_type] || "🎁"}</div>
         <div class="name">${escapeHtml(award.name)}</div>
       </div>`;
  });
  cells[4] =
    `<button id="spin-btn" class="spin"><span>抽奖</span><em id="spin-note">立即抽</em></button>`;
  $("grid").innerHTML = cells.join("");
  bindSpin();
  setActive(activeK);
}

function setActive(k) {
  document.querySelectorAll(".cell").forEach((el) => el.classList.remove("active"));
  const el = document.querySelector(`.cell[data-k="${k}"]`);
  if (el) el.classList.add("active");
  activeK = k;
}

/**
 * 高亮沿外圈跑若干圈后停在目标格。
 *
 * 目标格由**后端返回的奖品**决定，前端只负责让它停在对的位置——
 * 绝不能在前端再随机一次，否则界面显示的结果和真实落库的订单会对不上。
 */
async function runHighlight(targetK) {
  const loops = 3;
  const from = activeK;
  const steps = loops * 8 + (((targetK - from) % 8) + 8) % 8;
  document.querySelectorAll(".cell").forEach((el) => el.classList.remove("landed"));

  for (let i = 1; i <= steps; i++) {
    setActive((from + i) % 8);
    // 缓出：开始快、越接近终点越慢，是这类抽奖动画的标准手感
    await sleep(40 + 300 * Math.pow(i / steps, 2.8));
  }
  const el = document.querySelector(`.cell[data-k="${targetK}"]`);
  if (el) el.classList.add("landed");
}

/** 在属于该奖品的若干格子里随便挑一个落点——同一奖品占了多格，落哪个都合法。 */
function pickCellFor(awardId) {
  const idx = slots
    .map((a, k) => (a.award_id === awardId ? k : -1))
    .filter((k) => k >= 0);
  return idx.length ? idx[Math.floor(Math.random() * idx.length)] : 0;
}

function buildLights() {
  const box = $("lights");
  const n = 20;
  // 沿圆角矩形边框铺一圈灯珠
  box.innerHTML = Array.from({ length: n }, (_, i) => {
    const t = i / n;
    let x, y;
    if (t < 0.25) { x = t * 4 * 100; y = 0; }
    else if (t < 0.5) { x = 100; y = (t - 0.25) * 4 * 100; }
    else if (t < 0.75) { x = 100 - (t - 0.5) * 4 * 100; y = 100; }
    else { x = 0; y = 100 - (t - 0.75) * 4 * 100; }
    return `<i style="left:${x}%;top:${y}%;animation-delay:${(i % 6) * 0.18}s"></i>`;
  }).join("");
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
  slots = buildSlots(awards);
  renderGrid();

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

function bindSpin() {
  $("spin-btn").onclick = onSpin;
}

async function onSpin() {
  const btn = $("spin-btn");
  btn.disabled = true;
  $("spin-note").textContent = "抽奖中";

  const payload = {
    request_id: uuid(),
    user_id: $("user-id").value.trim() || "demo_user",
    activity_id: ACTIVITY_ID,
  };
  const { status, data } = await api("POST", "/api/lottery/draw", payload);
  // 用数组 join 拼多行文本，不写 \n 转义——
  // 这段代码是脚本生成的，转义序列在层层引号间传递时会被改写成真实换行，
  // 塞进 JS 字符串字面量里就是语法错误。
  $("draw-raw").textContent = [
    "POST /api/lottery/draw",
    JSON.stringify(payload, null, 2),
    "",
    "<- HTTP " + status,
    JSON.stringify(data, null, 2),
  ].join(String.fromCharCode(10));

  // 被拒绝就不跑灯：跑完 3 秒再说"你被限流了"很莫名其妙。
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
  await runHighlight(pickCellFor(landing));

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
  $("spin-btn").disabled = false;
  $("spin-note").textContent = "立即抽";
}

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
