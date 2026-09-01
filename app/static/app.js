const healthEl = document.getElementById("health-status");
const countrySelect = document.getElementById("country-select");
const projectTypeInput = document.getElementById("project-type");
const btnProfile = document.getElementById("btn-profile");
const profileResult = document.getElementById("profile-result");
const apiStatusEl = document.getElementById("api-status");
const apiDialog = document.getElementById("api-dialog");
const apiForm = document.getElementById("api-form");
const apiKeyInput = document.getElementById("api-key-input");
const apiMessage = document.getElementById("api-message");
const btnApiSave = document.getElementById("btn-api-save");

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

async function checkApiStatus() {
  try {
    const res = await fetch("/api/config/status");
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "状态读取失败");
    apiStatusEl.textContent = data.configured ? `API 已配置 · ${data.model}` : "API 未配置";
    apiStatusEl.classList.toggle("ok", data.configured);
    apiStatusEl.classList.toggle("warning", !data.configured);
  } catch {
    apiStatusEl.textContent = "API 状态未知";
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

function renderAnalysis(data) {
  return `
    <section class="analysis-card">
      <div class="analysis-heading">
        <h2>AI 综合研判</h2>
        <span class="model-tag">${escapeHtml(data.model)}</span>
      </div>
      <div class="analysis-text">${escapeHtml(data.analysis)}</div>
      <p class="disclaimer">AI 生成内容仅用于辅助研判，关键事实、来源和行动建议需要人工复核。</p>
    </section>`;
}

async function generateProfile() {
  const code = countrySelect.value;
  if (!code) return;
  profileResult.innerHTML = "<p>生成中…</p>";
  try {
    const res = await fetch(`/api/risk/${encodeURIComponent(code)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "请求失败");
    profileResult.innerHTML = `${renderProfile(data)}<p class="ai-loading">正在调用 AI 生成综合研判…</p>`;

    const analysisRes = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        country_code: code,
        project_type: projectTypeInput.value.trim() || "EPC工程总承包",
      }),
    });
    const analysisData = await analysisRes.json();
    if (!analysisRes.ok) throw new Error(analysisData.detail || "AI 分析请求失败");
    profileResult.querySelector(".ai-loading")?.remove();
    profileResult.insertAdjacentHTML("beforeend", renderAnalysis(analysisData));
  } catch (err) {
    const loading = profileResult.querySelector(".ai-loading");
    if (loading) {
      loading.className = "error analysis-error";
      loading.textContent = err.message;
    } else {
      profileResult.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
    }
  }
}

function closeApiDialog() {
  apiDialog.close();
  apiForm.reset();
  apiMessage.textContent = "";
}

document.getElementById("btn-api").addEventListener("click", () => {
  apiMessage.textContent = "";
  apiDialog.showModal();
  apiKeyInput.focus();
});
document.getElementById("btn-api-close").addEventListener("click", closeApiDialog);
document.getElementById("btn-api-cancel").addEventListener("click", closeApiDialog);
apiDialog.addEventListener("click", (event) => {
  if (event.target === apiDialog) closeApiDialog();
});
apiForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const apiKey = apiKeyInput.value.trim();
  if (!apiKey) return;
  btnApiSave.disabled = true;
  apiMessage.className = "form-message";
  apiMessage.textContent = "正在保存…";
  try {
    const res = await fetch("/api/config/api-key", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: apiKey }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "保存失败");
    apiKeyInput.value = "";
    apiMessage.className = "form-message success";
    apiMessage.textContent = `已保存到 ${data.saved_to}，当前服务已启用。`;
    await checkApiStatus();
    window.setTimeout(closeApiDialog, 900);
  } catch (err) {
    apiMessage.className = "form-message error";
    apiMessage.textContent = err.message;
  } finally {
    btnApiSave.disabled = false;
  }
});

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
checkApiStatus();
loadCountries();
