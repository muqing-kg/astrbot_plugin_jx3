const statusEl = document.getElementById("status");
const cardsEl = document.getElementById("cards");
let bridge = null;

function setStatus(text, isError = false) {
  if (!text) {
    statusEl.hidden = true;
    statusEl.textContent = "";
    return;
  }
  statusEl.hidden = false;
  statusEl.textContent = text;
  statusEl.classList.toggle("error", Boolean(isError));
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
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.message || data.msg || `HTTP ${response.status}`);
      return data;
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

function pill(label, on) {
  return `<span class="pill ${on ? "on" : ""}">${escapeHtml(label)}</span>`;
}

function render(payload) {
  const sessions = payload.sessions || [];
  cardsEl.innerHTML = "";
  if (!sessions.length) {
    cardsEl.innerHTML = '<div class="empty">暂无已绑定区服的群/私聊。先在对应会话发送 /绑定 区服名。</div>';
    return;
  }
  for (const row of sessions) {
    cardsEl.appendChild(sessionCard(row));
  }
}

function sessionCard(row) {
  const card = document.createElement("article");
  card.className = "card";
  card.innerHTML = `
    <div class="card-head">
      <div>
        <h2 class="card-title">${escapeHtml(row.display_name || "未命名会话")}</h2>
        <p class="umo">${escapeHtml(row.umo || "")}</p>
      </div>
      <div class="pills">
        ${pill(row.server || "未绑定区服", Boolean(row.server))}
        ${pill("Token " + (row.token_status || "未配置"), Boolean(row.has_token || row.use_global_token))}
        ${pill("推栏 " + (row.ticket_status || "未配置"), Boolean(row.has_ticket))}
        ${pill(row.bot_enabled === false ? "机器人已关闭" : "机器人开启", row.bot_enabled !== false)}
      </div>
    </div>
    <div class="switches">
      <label class="toggle">
        <input data-k="bot_enabled" type="checkbox" ${row.bot_enabled === false ? "" : "checked"} />
        启用该会话机器人
      </label>
      <label class="toggle">
        <input data-k="use_global" type="checkbox" ${row.use_global_token ? "checked" : ""} />
        使用全局 JX3API Token
      </label>
    </div>
    <div class="rows">
      <div class="row">
        <label class="field">
          <span>区服</span>
          <input data-k="server" placeholder="例如梦江南" value="${escapeHtml(row.server || "")}" />
        </label>
        <div class="row-actions">
          <button data-act="bind" type="button">保存区服</button>
          <button data-act="clear-server" class="ghost" type="button">清除区服</button>
        </div>
      </div>
      <div class="row">
        <label class="field">
          <span>JX3API Token</span>
          <input data-k="token" type="password" placeholder="填写后保存，不回显原文" />
        </label>
        <div class="row-actions">
          <button data-act="token" type="button">保存 Token</button>
          <button data-act="clear-token" class="ghost" type="button">清除 Token</button>
        </div>
      </div>
      <div class="row">
        <label class="field">
          <span>推栏标识</span>
          <input data-k="ticket" type="password" placeholder="填写后保存，不回显原文" />
        </label>
        <div class="row-actions">
          <button data-act="ticket" type="button">保存推栏</button>
          <button data-act="clear-ticket" class="ghost" type="button">清除推栏</button>
        </div>
      </div>
    </div>
  `;

  const run = async (fn) => {
    try {
      await fn();
      setStatus("已保存");
      await load();
    } catch (err) {
      setStatus(err.message || "保存失败", true);
    }
  };

  card.addEventListener("click", async (ev) => {
    const btn = ev.target.closest("button");
    if (!btn) return;
    const act = btn.dataset.act;
    const server = card.querySelector('[data-k="server"]').value.trim();
    const token = card.querySelector('[data-k="token"]').value.trim();
    const ticket = card.querySelector('[data-k="ticket"]').value.trim();
    if (act === "bind") {
      if (!row.umo || !server) return setStatus("请填写区服", true);
      await run(() => apiPost("page/sessions/bind", { umo: row.umo, server }));
    } else if (act === "token") {
      if (!row.umo || !token) return setStatus("请填写 Token", true);
      await run(() => apiPost("page/sessions/token", { umo: row.umo, token }));
    } else if (act === "ticket") {
      if (!row.umo || !ticket) return setStatus("请填写推栏标识", true);
      await run(() => apiPost("page/sessions/ticket", { umo: row.umo, ticket }));
    } else if (act === "clear-server") {
      await run(() => apiPost("page/sessions/clear-server", { umo: row.umo }));
    } else if (act === "clear-token") {
      await run(() => apiPost("page/sessions/clear-secret", { umo: row.umo, kind: "token" }));
    } else if (act === "clear-ticket") {
      await run(() => apiPost("page/sessions/clear-secret", { umo: row.umo, kind: "ticket" }));
    }
  });

  card.querySelector('[data-k="use_global"]').addEventListener("change", async (ev) => {
    const enabled = ev.target.checked;
    try {
      if (!row.umo) throw new Error("当前会话缺少标识");
      await apiPost("page/sessions/use-global", { umo: row.umo, enabled });
      setStatus(enabled ? "已启用全局 JX3API Token" : "已关闭全局 JX3API Token");
      await load();
    } catch (err) {
      ev.target.checked = !enabled;
      setStatus(err.message || "保存失败", true);
    }
  });
  card.querySelector('[data-k="bot_enabled"]').addEventListener("change", async (ev) => {
    const enabled = ev.target.checked;
    try {
      if (!row.umo) throw new Error("当前会话缺少标识");
      await apiPost("page/sessions/bot", { umo: row.umo, enabled });
      setStatus(enabled ? "已开启该会话机器人" : "已关闭该会话机器人");
      await load();
    } catch (err) {
      ev.target.checked = !enabled;
      setStatus(err.message || "保存失败", true);
    }
  });
  return card;
}

async function load() {
  const data = await apiGet("page/sessions");
  render(data);
}

document.getElementById("refreshBtn").addEventListener("click", () => {
  load().then(() => setStatus("已刷新")).catch((e) => setStatus(e.message, true));
});

waitForPluginBridge()
  .then((readyBridge) => {
    bridge = readyBridge;
    return load();
  })
  .catch((e) => setStatus(e.message, true));
