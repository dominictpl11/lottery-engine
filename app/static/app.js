// 面向用户的抽奖页。
//
// 刻意不展示中奖概率：九宫格里每个奖品占的格子数是平均的，奖品卡上也不标概率。
// 真实的中奖率只存在于后端的 weight 里，界面不泄露任何可用来反推的信息。
// 需要看概率和并发行为的，去 /dev。

// 3x3 布局，中间是按钮，外圈 8 格顺时针的 DOM 下标：
//   0 1 2
//   3 4 5      ->  0 -> 1 -> 2 -> 5 -> 8 -> 7 -> 6 -> 3 -> 回到 0
//   6 7 8
const PERIMETER = [0, 1, 2, 5, 8, 7, 6, 3];

let awards = [];
let slots = [];        // 长度 8，slots[k] 对应 PERIMETER[k] 那一格
let activeK = 0;
let dailyLimit = 0;
let usedToday = 0;     // 本会话内该用户已参与次数，仅用于界面提示

/**
 * 把奖品铺进 8 个格子。
 *
 * 刻意**平均分配**而不是按权重：如果概率高的奖品占更多格子，用户数一下格子就能
 * 反推出中奖率。4 个奖品各占 2 格轮流铺开，格子数不携带任何信息。
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
  $("spin-btn").onclick = onSpin;
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
  const steps = loops * 8 + ((((targetK - from) % 8) + 8) % 8);
  document.querySelectorAll(".cell").forEach((el) => el.classList.remove("landed"));

  for (let i = 1; i <= steps; i++) {
    setActive((from + i) % 8);
    // 缓出：开始快、越接近终点越慢，是这类抽奖动画的标准手感
    await sleep(40 + 300 * Math.pow(i / steps, 2.8));
  }
  const el = document.querySelector(`.cell[data-k="${targetK}"]`);
  if (el) el.classList.add("landed");
}

/** 同一奖品占了多格，落哪一格都合法，随便挑一个。 */
function pickCellFor(awardId) {
  const idx = slots.map((a, k) => (a.award_id === awardId ? k : -1)).filter((k) => k >= 0);
  return idx.length ? idx[Math.floor(Math.random() * idx.length)] : 0;
}

function buildLights() {
  const box = $("lights");
  const n = 20;
  box.innerHTML = Array.from({ length: n }, (_, i) => {
    const t = i / n;
    let x, y;
    if (t < 0.25) { x = t * 400; y = 0; }
    else if (t < 0.5) { x = 100; y = (t - 0.25) * 400; }
    else if (t < 0.75) { x = 100 - (t - 0.5) * 400; y = 100; }
    else { x = 0; y = 100 - (t - 0.75) * 400; }
    return `<i style="left:${x}%;top:${y}%;animation-delay:${(i % 6) * 0.18}s"></i>`;
  }).join("");
}

// ---------- 中奖播报 ----------
// 只播真实发生过的抽奖（本次会话在这个页面抽出来的），不编造假数据。

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
  track.innerHTML = feed.slice(-8).map((t) => `<div class="marquee-item">${t}</div>`).join("");
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

async function loadActivity() {
  const [act, aw] = await Promise.all([
    api("GET", `/api/activities/${ACTIVITY_ID}`),
    api("GET", `/api/activities/${ACTIVITY_ID}/awards`),
  ]);

  if (act.status === 404) {
    $("activity-sub").textContent = `活动 ${ACTIVITY_ID} 不存在`;
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

  // 奖品卡不标概率——标了就等于把中奖率直接告诉用户，
  // 那九宫格刻意做成平均格子数就白费了。只展示还剩多少，制造稀缺感。
  $("prizes").innerHTML = awards.map((w) => `
    <div class="prize ${w.stock_surplus === 0 ? "sold-out" : ""}">
      <div class="emoji">${EMOJI[w.award_type] || "🎁"}</div>
      <div class="name">${escapeHtml(w.name)}</div>
      <div class="meta">${w.award_type === "none" ? "再接再厉" : `仅剩 ${w.stock_surplus} 份`}</div>
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

async function onSpin() {
  const btn = $("spin-btn");
  btn.disabled = true;
  $("spin-note").textContent = "抽奖中";

  const { status, data } = await api("POST", "/api/lottery/draw", {
    request_id: uuid(),
    user_id: currentUser(),
    activity_id: ACTIVITY_ID,
  });

  // 被拒绝就不跑灯：跑完 3 秒再说"你被限流了"很莫名其妙。
  if (status !== 200 || data.draw_state === "rejected") {
    showReject(status, data);
    $("spin-btn").disabled = false;
    $("spin-note").textContent = "立即抽";
    return;
  }

  usedToday += 1;
  $("left-count").textContent = Math.max(dailyLimit - usedToday, 0);

  const won = data.draw_state === "won";
  await runHighlight(pickCellFor(won ? data.award.award_id : idOfThanks()));

  if (won) {
    pushFeed(currentUser(), data.award.award_name);
    showModal({ icon: "🎉", title: "恭喜获得", prize: data.award.award_name,
                note: `订单 ${data.order_id.slice(0, 12)}…`, button: "开心收下" });
  } else {
    showModal({ icon: "🙏", title: "谢谢参与", prize: "下次再来试试",
                note: `订单 ${data.order_id.slice(0, 12)}…`, variant: "miss", button: "再来一次" });
  }

  await loadActivity();
  $("spin-btn").disabled = false;
  $("spin-note").textContent = "立即抽";
}

/**
 * 用户身份。真实产品会从登录态拿，这里没有账号体系（见 README 的 Known Limitations），
 * 所以在浏览器本地生成一个并记住，至少让"每人每日 N 次"这条规则有意义。
 */
function currentUser() {
  let u = localStorage.getItem("lottery_uid");
  if (!u) {
    u = "u_" + uuid().slice(0, 10);
    localStorage.setItem("lottery_uid", u);
  }
  return u;
}

/** missed 时后端不返回 award 对象，落在"谢谢参与"格子上。 */
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
    return showModal({ icon: "⏱️", title: "请勿重复提交", prize: "上一次还在处理中", variant: "reject" });
  }
  if (status === 404) {
    return showModal({ icon: "❓", title: "活动不存在", variant: "reject" });
  }
  if (status >= 500) {
    return showModal({ icon: "⚠️", title: status === 503 ? "服务繁忙，请稍后再试" : "系统繁忙",
                       variant: "reject" });
  }
  const [icon, title, note] = REJECT_TEXT[d.reject_reason] || ["😅", d.message, ""];
  showModal({ icon, title, prize: note, variant: "reject" });
}

buildLights();
renderFeed();
loadActivity();
