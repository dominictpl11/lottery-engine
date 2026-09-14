// 两个页面共用的最小工具集。
// / 是面向用户的抽奖页，/dev 是开发者页，两者只共享这些基础函数。

const ACTIVITY_ID = 100001;

const $ = (id) => document.getElementById(id);
const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2) + Date.now());
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 奖品类型到图标。纯展示用，后端不关心。
const EMOJI = { physical: "📱", coupon: "🎟️", virtual: "💎", none: "🙏" };

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

/** 拼多行文本。刻意不写换行转义——见 DEVLOG 里关于转义折叠的记录。 */
function lines(...parts) {
  return parts.join(String.fromCharCode(10));
}
