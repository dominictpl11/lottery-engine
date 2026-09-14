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
  try { data = await res.json(); } catch (_) { /* 204 之类 */ }
  return { status: res.status, data };
}

// ---------- 活动与奖品 ----------

async function loadActivity() {
  const [act, awards] = await Promise.all([
    api("GET", `/api/activities/${ACTIVITY_ID}`),
    api("GET", `/api/activities/${ACTIVITY_ID}/awards`),
  ]);

  if (act.status === 404) {
    $("activity-info").innerHTML =
      `<span class="tag error">活动不存在</span> 先跑一次 seed 脚本创建活动 ${ACTIVITY_ID}`;
    return;
  }
  const a = act.data;
  $("activity-info").innerHTML =
    `<strong>${escapeHtml(a.name)}</strong> · 活动库存 ` +
    `<code>${a.stock_surplus} / ${a.stock_total}</code> · ` +
    `每人每日 <code>${a.daily_limit}</code> 次 · ` +
    `<span class="tag ${a.status === "running" ? "won" : "rejected"}">${a.status}</span>`;

  const total = (awards.data || []).reduce((s, w) => s + w.weight, 0) || 1;
  $("award-table").querySelector("tbody").innerHTML = (awards.data || [])
    .map((w) => `
      <tr class="${w.stock_surplus === 0 ? "sold-out" : ""}">
        <td>${escapeHtml(w.name)}</td>
        <td><code>${w.award_type}</code></td>
        <td class="num">${((w.weight / total) * 100).toFixed(1)}%</td>
        <td class="num">${w.stock_surplus} / ${w.stock_total}</td>
      </tr>`)
    .join("");
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

// ---------- 单次抽奖 ----------

$("new-user").onclick = () => { $("user-id").value = "u_" + uuid().slice(0, 8); };

$("draw-btn").onclick = async () => {
  const btn = $("draw-btn");
  btn.disabled = true;
  const payload = {
    request_id: uuid(),
    user_id: $("user-id").value.trim() || "demo_user",
    activity_id: ACTIVITY_ID,
  };
  const { status, data } = await api("POST", "/api/lottery/draw", payload);
  renderDraw(status, data);
  $("draw-raw").textContent =
    "POST /api/lottery/draw\n" + JSON.stringify(payload, null, 2) +
    `\n\n<- HTTP ${status}\n` + JSON.stringify(data, null, 2);
  await loadActivity();
  btn.disabled = false;
};

function renderDraw(status, d) {
  const box = $("draw-result");
  if (status >= 500) {
    box.className = "result error";
    box.innerHTML = `<span class="tag error">HTTP ${status}</span>
      <span class="big">${escapeHtml(d && d.detail || "系统错误")}</span>`;
    return;
  }
  if (status === 404) {
    box.className = "result error";
    box.innerHTML = `<span class="tag error">404</span><span class="big">活动不存在</span>`;
    return;
  }
  if (status === 409) {
    box.className = "result rejected";
    box.innerHTML = `<span class="tag rejected">409</span>
      <span class="big">同一 request_id 正在处理中</span>`;
    return;
  }
  const state = d.draw_state;
  box.className = "result " + state;
  const label = state === "won"
    ? `🎉 ${escapeHtml(d.award.award_name)}`
    : state === "missed" ? "未中奖" : escapeHtml(d.message);
  const extra = state === "rejected"
    ? `<code>${d.reject_reason}</code>`
    : `<span class="muted">order <code>${d.order_id.slice(0, 12)}…</code></span>`;
  box.innerHTML = `<span class="tag ${state}">${state}</span>
    <span class="big">${label}</span> ${extra}`;
}

// ---------- 并发测试 ----------

$("burst-btn").onclick = async () => {
  const btn = $("burst-btn");
  const n = Math.max(1, Math.min(500, parseInt($("burst-n").value, 10) || 100));
  const sameUser = $("burst-same-user").checked;
  const sameReq = $("burst-same-req").checked;

  btn.disabled = true;
  $("burst-result").innerHTML = `<p class="muted">正在并发打出 ${n} 个请求…</p>`;

  // 打之前先记下库存，跑完对账
  const before = (await api("GET", `/api/activities/${ACTIVITY_ID}`)).data;

  const fixedReq = uuid();
  const t0 = performance.now();
  const results = await Promise.all(
    Array.from({ length: n }, (_, i) =>
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
    {
      ok: after.stock_surplus >= 0,
      text: `库存未被扣成负数（剩余 ${after.stock_surplus}）`,
    },
    {
      ok: drawn === consumed,
      text: `产生的订单数 ${drawn} == 实际消耗库存 ${consumed}`,
    },
    {
      ok: after.stock_surplus <= before.stock_surplus,
      text: `库存只减不增（${before.stock_surplus} -> ${after.stock_surplus}）`,
    },
  ];
  if (sameReq) {
    checks.push({
      ok: orderIds.size <= 1 && consumed <= 1,
      text: `同一 request_id 只产生 ${orderIds.size} 个订单、只扣 ${consumed} 个库存（幂等）`,
    });
  }
  const allOk = checks.every((c) => c.ok);

  const rows = Object.entries(tally)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `<tr><td>${escapeHtml(k)}</td><td class="num">${v}</td></tr>`)
    .join("");

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
