const healthEl = document.getElementById("health-status");
const countrySelect = document.getElementById("country-select");
const projectTypeInput = document.getElementById("project-type");
const btnProfile = document.getElementById("btn-profile");
const profileResult = document.getElementById("profile-result");

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    healthEl.textContent = data.status === "ok" ? "服务正常" : "服务异常";
    healthEl.classList.add("ok");
  } catch {
    healthEl.textContent = "无法连接服务";
  }
}

async function loadCountries() {
  try {
    const res = await fetch("/api/countries");
    const data = await res.json();
    countrySelect.innerHTML = "";
    for (const c of data.countries) {
      const opt = document.createElement("option");
      opt.value = c.code;
      opt.textContent = `${c.name_zh}（${c.code}）`;
      countrySelect.appendChild(opt);
    }
  } catch {
    countrySelect.innerHTML = "<option>加载失败</option>";
  }
}

function levelClass(level) {
  return level === "高" ? "level-high" : level === "中" ? "level-mid" : "level-low";
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function renderProfile(p) {
  const dims = p.dimensions.map((d) => `
    <div class="card">
      <h3>${d.name} <span class="score ${levelClass(d.level)}">${d.score} 分 · ${d.level}</span></h3>
      <ul>${d.evidence.map((e) => `<li>${escapeHtml(e)}</li>`).join("")}</ul>
    </div>`).join("");
  return `
    <div class="overview">
      <h2>${escapeHtml(p.country_name)}（${p.country_code}）综合风险：
      <span class="score ${levelClass(p.overall_level)}">${p.overall_score} 分 · ${p.overall_level}</span></h2>
    </div>
    <div class="cards">${dims}</div>`;
}

async function generateProfile() {
  const code = countrySelect.value;
  if (!code) return;
  profileResult.innerHTML = "<p>生成中…</p>";
  try {
    const res = await fetch(`/api/risk/${encodeURIComponent(code)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "请求失败");
    profileResult.innerHTML = renderProfile(data);
  } catch (err) {
    profileResult.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
  }
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.add("hidden"));
    btn.classList.add("active");
    document.getElementById(`panel-${btn.dataset.tab}`).classList.remove("hidden");
  });
});

btnProfile.addEventListener("click", generateProfile);
checkHealth();
loadCountries();
