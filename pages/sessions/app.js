const statusEl = document.getElementById("status");
const rowsEl = document.getElementById("rows");
let bridge = null;

function setStatus(text) {
  statusEl.textContent = text || "";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function createDevFallbackBridge() {
  const apiBase = "/api/plugin/astrbot_plugin_jx3/";
  return {
    apiGet: async (endpoint, params = {}) => {
      const url = new URL(`${apiBase}${endpoint}`, window.location.origin);
      Object.entries(params || {}).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
      });
      const response = await fetch(url, { credentials: "same-origin" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    },
    apiPost: async (endpoint, body = {}) => {
      const response = await fetch(`${apiBase}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(body),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.message || data.msg || `HTTP ${response.status}`);
      return data;
    },
  };
}

function waitForPluginBridge(timeoutMs = 8000) {
  if (window.AstrBotPluginPage) return Promise.resolve(window.AstrBotPluginPage);
  return new Promise((resolve, reject) => {
    const started = Date.now();
    const timer = window.setInterval(() => {
      if (window.AstrBotPluginPage) {
        window.clearInterval(timer);
        resolve(window.AstrBotPluginPage);
        return;
      }
      if (Date.now() - started >= timeoutMs) {
        window.clearInterval(timer);
        if (window.parent && window.parent !== window) {
          reject(new Error("Plugin page bridge is not ready"));
          return;
        }
        resolve(createDevFallbackBridge());
      }
    }, 50);
  });
}

async function apiGet(endpoint, params) {
  return bridge.apiGet(endpoint, params);
}

async function apiPost(endpoint, body) {
  return bridge.apiPost(endpoint, body);
}

function boolText(v) {
  return v ? "开" : "关";
}

function render(payload) {
  const sessions = payload.sessions || [];
  rowsEl.innerHTML = "";
  if (!sessions.length) {
    rowsEl.innerHTML = '<tr><td colspan="11">暂无会话。群里先发一条指令或完成绑定后会出现在这里。</td></tr>';
    return;
  }
  for (const row of sessions) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(row.display_name || "-")}</td>
      <td class="umo">${escapeHtml(row.umo)}</td>
      <td>${escapeHtml(row.server || "未绑定")}</td>
      <td>${escapeHtml(row.token_status)}</td>
      <td>${escapeHtml(row.ticket_status)}</td>
      <td>${row.use_global_token ? "是" : "否"}</td>
      <td>${boolText(row.push_kaifu)}</td>
      <td>${boolText(row.push_xinwen)}</td>
      <td>${boolText(row.push_shuma)}</td>
      <td>${boolText(row.push_chitu)}</td>
      <td class="ops"></td>
    `;
    tr.querySelector(".ops").appendChild(actionRow(row));
    rowsEl.appendChild(tr);
  }
}

function actionRow(row) {
  const box = document.createElement("div");
  box.className = "ops";
  box.innerHTML = `
    <input data-k="server" placeholder="区服，如梦江南" value="${escapeHtml(row.server || "")}" />
    <button data-act="bind">保存区服</button>
    <label><input type="checkbox" data-k="use_global" ${row.use_global_token ? "checked" : ""}/> 使用全局Token</label>
    <input data-k="token" type="password" placeholder="填写后保存 Token" />
    <button data-act="token">保存Token</button>
    <button data-act="clear-token">清除Token</button>
    <input data-k="ticket" type="password" placeholder="填写后保存推栏" />
    <button data-act="ticket">保存推栏</button>
    <button data-act="clear-ticket">清除推栏</button>
    <div>
      <button data-act="push" data-kind="开服" data-on="${row.push_kaifu ? 0 : 1}">${row.push_kaifu ? "关闭开服" : "打开开服"}</button>
      <button data-act="push" data-kind="新闻" data-on="${row.push_xinwen ? 0 : 1}">${row.push_xinwen ? "关闭新闻" : "打开新闻"}</button>
      <button data-act="push" data-kind="刷马" data-on="${row.push_shuma ? 0 : 1}">${row.push_shuma ? "关闭刷马" : "打开刷马"}</button>
      <button data-act="push" data-kind="赤兔" data-on="${row.push_chitu ? 0 : 1}">${row.push_chitu ? "关闭赤兔" : "打开赤兔"}</button>
    </div>
  `;
  box.addEventListener("click", async (ev) => {
    const btn = ev.target.closest("button");
    if (!btn) return;
    const act = btn.dataset.act;
    try {
      if (act === "bind") {
        await apiPost("page/sessions/bind", { umo: row.umo, server: box.querySelector('[data-k="server"]').value });
      } else if (act === "token") {
        await apiPost("page/sessions/token", { umo: row.umo, token: box.querySelector('[data-k="token"]').value });
      } else if (act === "ticket") {
        await apiPost("page/sessions/ticket", { umo: row.umo, ticket: box.querySelector('[data-k="ticket"]').value });
      } else if (act === "clear-token") {
        await apiPost("page/sessions/clear-secret", { umo: row.umo, kind: "token" });
      } else if (act === "clear-ticket") {
        await apiPost("page/sessions/clear-secret", { umo: row.umo, kind: "ticket" });
      } else if (act === "push") {
        await apiPost("page/sessions/push", { umo: row.umo, kind: btn.dataset.kind, enabled: btn.dataset.on === "1" });
      }
      setStatus("已保存");
      await load();
    } catch (err) {
      setStatus(err.message);
    }
  });
  box.querySelector('[data-k="use_global"]').addEventListener("change", async (ev) => {
    try {
      await apiPost("page/sessions/use-global", { umo: row.umo, enabled: ev.target.checked });
      setStatus("已保存");
      await load();
    } catch (err) {
      setStatus(err.message);
    }
  });
  return box;
}

async function load() {
  const data = await apiGet("page/sessions");
  render(data);
}

document.getElementById("refreshBtn").addEventListener("click", () => load().catch((e) => setStatus(e.message)));

waitForPluginBridge()
  .then((readyBridge) => {
    bridge = readyBridge;
    return load();
  })
  .catch((e) => setStatus(e.message));
