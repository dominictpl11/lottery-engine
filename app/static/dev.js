// 开发者页。与用户页的区别：这里把后端的真实配置和并发行为直接摊开。

async function loadActivity() {
  const [act, aw] = await Promise.all([
    api("GET", `/api/activities/${ACTIVITY_ID}`),
    api("GET", `/api/activities/${ACTIVITY_ID}/awards`),
  ]);
  if (act.status === 404) {
    $("activity-info").innerHTML = `活动 <code>${ACTIVITY_ID}</code> 不存在，需要先创建`;
    return;
  }
  const a = act.data;
  $("activity-info").innerHTML =
    `<strong>${escapeHtml(a.name)}</strong> · 状态 <code>${a.status}</code> · ` +
    `活动库存 <code>${a.stock_surplus} / ${a.stock_total}</code> · ` +
    `每人每日 <code>${a.daily_limit}</code> 次<br>` +
    `<span class="muted">${escapeHtml(a.start_time)} ~ ${escapeHtml(a.end_time)}</span>`;

  const list = aw.data || [];
  const total = list.reduce((s, w) => s + w.weight, 0) || 1;
  $("award-table").querySelector("tbody").innerHTML = list.map((w) => `
    <tr>
      <td>${EMOJI[w.award_type] || "🎁"} ${escapeHtml(w.name)}</td>
      <td><code>${w.award_type}</code></td>
      <td class="num">${w.weight}</td>
      <td class="num">${((w.weight / total) * 100).toFixed(2)}%</td>
      <td class="num">${w.stock_surplus} / ${w.stock_total}</td>
    </tr>`).join("");
}

// ---------- 单次抽奖 ----------

$("new-user").onclick = () => { $("user-id").value = "u_" + uuid().slice(0, 8); };

$("draw-btn").onclick = async () => {
  const btn = $("draw-btn");
  btn.disabled = true;
  const payload = {
    request_id: uuid(),
    user_id: $("user-id").value.trim() || "dev_user",
    activity_id: ACTIVITY_ID,
  };
  const { status, data } = await api("POST", "/api/lottery/draw", payload);
  $("draw-raw").textContent = lines(
    "POST /api/lottery/draw",
    JSON.stringify(payload, null, 2),
    "",
    "<- HTTP " + status,
    JSON.stringify(data, null, 2),
  );
  await loadActivity();
  btn.disabled = false;
};

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
    else if (status >= 500) key = `HTTP ${status}`;
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
