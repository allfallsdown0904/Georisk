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

// ---------- RAG 智能体分析（事件预警 / 情景推演 / 建议清单） ----------
const questionInput = document.getElementById("question-input");
const btnAnalyze = document.getElementById("btn-analyze");
const ragModeEl = document.getElementById("rag-mode");
const alertResult = document.getElementById("alert-result");
const scenarioResult = document.getElementById("scenario-result");
const adviceResult = document.getElementById("advice-result");
let lastReport = null;

function dimCardHtml(dim) {
  return `<div class="card">
    <h3>${escapeHtml(dim.name)} <span class="score ${levelClass(dim.level)}">${dim.score} 分 · ${dim.level}</span></h3>
    <p class="dim-summary">${escapeHtml(dim.summary || "暂无说明")}</p>
  </div>`;
}

function badge(level) {
  return `<span class="score ${levelClass(level)}">${escapeHtml(level)}</span>`;
}

function renderAlert(report) {
  const dims = Object.values(report.dimensions).map(dimCardHtml).join("");
  const risks = (report.key_risks || []).map((r) => `
    <li class="risk-item">
      <strong>${escapeHtml(r.risk)}</strong> ${badge(r.likelihood || "中")}
      <p>${escapeHtml(r.impact || "")}</p>
      <p class="meta">证据：${(r.evidence || []).map(escapeHtml).join("、")} · 置信度 ${r.confidence ?? "-"}${r.needs_human_review ? " · <b class=\"verify\">待人工核实</b>" : ""}</p>
    </li>`).join("");
  const watch = (report.watchlist || []).map((w) => `<li>${escapeHtml(w)}</li>`).join("");
  return `
    <div class="overview">
      <h2>${escapeHtml(report.country)} · ${escapeHtml(report.project || "一般业务")} 综合风险：
        <span class="score ${levelClass(report.overall_risk)}">${report.overall_score} 分 · ${report.overall_risk}</span></h2>
    </div>
    <div class="cards">${dims}</div>
    <h3 class="section-title">关键风险（事件预警）</h3>
    <ul class="risk-list">${risks || "<li>暂无</li>"}</ul>
    <h3 class="section-title">监测清单（观察指标）</h3>
    <ul class="watch-list">${watch || "<li>暂无</li>"}</ul>`;
}

function renderScenarios(report) {
  const items = (report.scenarios || []).map((s) => `
    <div class="card scenario-card">
      <h3>${escapeHtml(s.name)}</h3>
      <p>${escapeHtml(s.summary)}</p>
      <ul>${(s.triggers || []).map((t) => `<li>${escapeHtml(t)}</li>`).join("")}</ul>
    </div>`).join("");
  return `<div class="cards scenarios">${items || "<div class=\"card\">暂无情景</div>"}</div>`;
}

function renderAdvice(report) {
  const recs = (report.recommendations || []).map((r) => `
    <div class="card advice-card">
      <h3>${badge(r.priority || "中")} ${escapeHtml(r.action)}</h3>
      <p class="meta">时间窗口：${escapeHtml(r.timeframe || "-")} · 成本估算：${escapeHtml(r.cost_estimate || "-")} · 置信度 ${r.confidence ?? "-"}${r.needs_human_review ? " · <b class=\"verify\">待人工核实</b>" : ""}</p>
      <p class="meta">证据：${(r.evidence || []).map(escapeHtml).join("、")}</p>
    </div>`).join("");
  const sources = (report.sources || []).map((s) => `
    <li class="source-item">
      <span class="tag">${s.type === "web_search" ? "联网" : "知识库"}</span>
      ${escapeHtml(s.title || s.source)}
      ${s.url ? `<a href="${escapeHtml(s.url)}" target="_blank" rel="noopener">来源链接</a>` : ""}
      <span class="meta">${escapeHtml(s.source)} · ${escapeHtml(s.date || "日期未知")} · 置信度 ${s.confidence ?? "-"}</span>
    </li>`).join("");
  return `
    <h3 class="section-title">个性化建议清单</h3>
    <div class="cards advice">${recs || "<div class=\"card\">暂无建议</div>"}</div>
    <h3 class="section-title">证据溯源（${report.sources.length}）</h3>
    <ul class="source-list">${sources || "<li>暂无</li>"}</ul>`;
}

function showModeNote(report) {
  if (!report.llm_unavailable) {
    ragModeEl.textContent = "模式：LLM 智能生成（联网检索补强）";
    ragModeEl.classList.add("ok");
  } else {
    ragModeEl.textContent = "模式：规则引擎（未配置 LLM_API_KEY，由知识库加权生成，仅供参考）";
    ragModeEl.classList.remove("ok");
  }
}

async function runRagAnalysis() {
  const code = countrySelect.value;
  if (!code) return;
  alertResult.innerHTML = "<p>分析中…</p>";
  try {
    const res = await fetch("/api/rag/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        country: code,
        project: projectTypeInput.value,
        question: questionInput.value,
        top_k: 12,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "请求失败");
    lastReport = data;
    showModeNote(data);
    alertResult.innerHTML = renderAlert(data);
    scenarioResult.innerHTML = renderScenarios(data);
    adviceResult.innerHTML = renderAdvice(data);
  } catch (err) {
    alertResult.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
  }
}

btnAnalyze.addEventListener("click", runRagAnalysis);

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (!lastReport && (btn.dataset.tab === "scenario" || btn.dataset.tab === "advice")) {
      const box = document.getElementById(`panel-${btn.dataset.tab}`).querySelector(".result");
      if (box && !box.innerHTML.trim()) {
        box.innerHTML = `<p class="placeholder">请先在「事件预警」页点击“开始智能分析”。</p>`;
      }
    }
  });
});