const statusEl = document.getElementById("status");
const cardsEl = document.getElementById("cards");
const commandListEl = document.getElementById("commandList");
const pushListEl = document.getElementById("pushList");
const serverListEl = document.getElementById("serverList");
const resetBtn = document.getElementById("resetBtn");
let bridge = null;
let currentView = "sessions";

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

function pill(label, on, title = "") {
  const titleAttribute = title ? ` title="${escapeHtml(title)}"` : "";
  return `<span class="pill ${on ? "on" : ""}"${titleAttribute}>${escapeHtml(label)}</span>`;
}

function setView(view) {
  currentView = view;
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === view);
  });
  document.querySelectorAll(".view-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.viewPanel === view);
  });
  resetBtn.hidden = view === "sessions";
}

function renderSessions(payload) {
  const sessions = payload.sessions || [];
  cardsEl.innerHTML = "";
  if (!sessions.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "暂无已绑定区服的群聊。先在对应群聊发送 绑定 区服名。";
    cardsEl.appendChild(empty);
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
        ${pill("认领人 " + (row.claim_name || row.claim_identity || "未认领"), Boolean(row.claim_identity))}
        ${pill(row.server || "未绑定区服", Boolean(row.server))}
        ${pill("Token " + (row.token_status || "未配置"), Boolean(row.has_token))}
        ${pill("推栏 " + (row.ticket_status || "未配置"), Boolean(row.has_ticket))}
        ${pill(row.bot_enabled === false ? "机器人已关闭" : "机器人开启", row.bot_enabled !== false)}
        ${pill(
          row.push_fail_count ? `推送异常 ${row.push_fail_count} 次` : "推送正常",
          !row.push_fail_count,
          row.push_last_error || ""
        )}
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
          <input data-k="token" data-initial="${escapeHtml(row.token_display_value || "")}" value="${escapeHtml(row.token_display_value || "")}" placeholder="多个用逗号分隔" />
        </label>
        <div class="row-actions">
          <button data-act="token" type="button">保存 Token</button>
          <button data-act="clear-token" class="ghost" type="button">清除 Token</button>
        </div>
      </div>
      <div class="row">
        <label class="field">
          <span>推栏标识</span>
          <input data-k="ticket" data-initial="${escapeHtml(row.ticket_display_value || "")}" value="${escapeHtml(row.ticket_display_value || "")}" placeholder="多个用逗号分隔" />
        </label>
        <div class="row-actions">
          <button data-act="ticket" type="button">保存推栏</button>
          <button data-act="clear-ticket" class="ghost" type="button">清除推栏</button>
        </div>
      </div>
      <div class="row">
        <label class="field">
          <span>授权管理 ID</span>
          <input data-k="managers" value="${escapeHtml((row.managers || []).map(m => (m.name && m.name !== m.id) ? `${m.name}（${m.id}）` : (m.id || m.name || "")).join(","))}" placeholder="保留或删除已有授权，多个用逗号分隔" />
        </label>
        <div class="row-actions">
          <button data-act="save-managers" type="button">保存管理</button>
        </div>
      </div>
      ${row.claim_identity ? `
      <div class="row">
        <label class="field">
          <span>认领人</span>
          <span class="static-text">${escapeHtml(row.claim_name || row.claim_identity)}</span>
        </label>
        <div class="row-actions">
          <button data-act="clear-claim" class="ghost" type="button">取消认领资格</button>
        </div>
      </div>
      ` : ""}
      <div class="row">
        <label class="field">
          <span>会话清理</span>
          <span class="static-text">删除会话会清空区服、Token、推栏、推送和管理员数据。</span>
        </label>
        <div class="row-actions">
          <button data-act="delete" class="danger" type="button">删除会话</button>
        </div>
      </div>
    </div>
  `;

  const run = async (fn) => {
    try {
      await fn();
      setStatus("已保存");
      await loadSessions();
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
    const managerEl = card.querySelector('[data-k="managers"]');
    const managers = managerEl ? managerEl.value.trim() : "";
    if (act === "bind") {
      if (!row.umo || !server) return setStatus("请填写区服", true);
      await run(() => bridge.apiPost("page/sessions/bind", { umo: row.umo, server }));
    } else if (act === "token") {
      if (!row.umo || !token) return setStatus("请填写 Token", true);
      if (token === (card.querySelector('[data-k="token"]').dataset.initial || "")) {
        return setStatus("Token 未修改，保持当前配置");
      }
      await run(() => bridge.apiPost("page/sessions/token", { umo: row.umo, token }));
    } else if (act === "ticket") {
      if (!row.umo || !ticket) return setStatus("请填写推栏标识", true);
      if (ticket === (card.querySelector('[data-k="ticket"]').dataset.initial || "")) {
        return setStatus("推栏标识未修改，保持当前配置");
      }
      await run(() => bridge.apiPost("page/sessions/ticket", { umo: row.umo, ticket }));
    } else if (act === "save-managers") {
      if (!row.umo) return setStatus("缺少 UMO", true);
      await run(() => bridge.apiPost("page/sessions/managers", { umo: row.umo, managers }));
    } else if (act === "clear-claim") {
      await run(() => bridge.apiPost("page/sessions/claim", { identity: row.claim_identity }));
    } else if (act === "clear-server") {
      await run(() => bridge.apiPost("page/sessions/clear-server", { umo: row.umo }));
    } else if (act === "clear-token") {
      await run(() => bridge.apiPost("page/sessions/clear-secret", { umo: row.umo, kind: "token" }));
    } else if (act === "clear-ticket") {
      await run(() => bridge.apiPost("page/sessions/clear-secret", { umo: row.umo, kind: "ticket" }));
    } else if (act === "delete") {
      const confirmed = window.confirm("确认删除该会话吗？将停止主动推送并清空该会话数据。");
      if (!confirmed) return;
      try {
        const result = await bridge.apiPost("page/sessions/delete", { umo: row.umo });
        setStatus(result.message || "已删除会话", !result.left);
        await loadSessions();
      } catch (err) {
        setStatus(err.message || "删除失败", true);
      }
    }
  });

  card.querySelector('[data-k="use_global"]').addEventListener("change", async (ev) => {
    const enabled = ev.target.checked;
    try {
      if (!row.umo) throw new Error("当前会话缺少标识");
      await bridge.apiPost("page/sessions/use-global", { umo: row.umo, enabled });
      setStatus(enabled ? "已启用全局 JX3API Token" : "已关闭全局 JX3API Token");
      await loadSessions();
    } catch (err) {
      ev.target.checked = !enabled;
      setStatus(err.message || "保存失败", true);
    }
  });
  card.querySelector('[data-k="bot_enabled"]').addEventListener("change", async (ev) => {
    const enabled = ev.target.checked;
    try {
      if (!row.umo) throw new Error("当前会话缺少标识");
      await bridge.apiPost("page/sessions/bot", { umo: row.umo, enabled });
      setStatus(enabled ? "已开启该会话机器人" : "已关闭该会话机器人");
      await loadSessions();
    } catch (err) {
      ev.target.checked = !enabled;
      setStatus(err.message || "保存失败", true);
    }
  });
  return card;
}

function renderCommands(payload) {
  const commands = payload.commands || [];
  commandListEl.innerHTML = `<div class="head"><span>命令</span><span>参数</span><span>功能描述</span><span></span></div>`;
  let currentGroup = "";
  for (const row of commands) {
    if (row.group && row.group !== currentGroup) {
      currentGroup = row.group;
      const head = document.createElement("div");
      head.className = "group-head";
      head.textContent = currentGroup;
      commandListEl.appendChild(head);
    }
    const el = document.createElement("div");
    el.className = "row";
    el.innerHTML = `
      <input data-k="command" value="${escapeHtml(row.command || "")}" />
      <div class="cell-text">${escapeHtml(row.params || "")}</div>
      <div class="cell-text">${escapeHtml(row.desc || "")}</div>
      <button data-act="save" type="button">保存</button>
    `;
    el.querySelector('[data-act="save"]').addEventListener("click", async () => {
      try {
        await bridge.apiPost("page/commands/save", {
          id: row.id,
          command: el.querySelector('[data-k="command"]').value.trim(),
        });
        setStatus("已保存");
        await loadCommands();
      } catch (err) {
        setStatus(err.message || "保存失败", true);
      }
    });
    commandListEl.appendChild(el);
  }
}

function renderPush(payload) {
  pushListEl.innerHTML = `<div class="head"><span>命令</span><span>参数</span><span>功能描述</span><span></span></div>`;
  for (const row of [payload.open, payload.close]) {
    const el = document.createElement("div");
    el.className = "row";
    el.innerHTML = `
      <input data-k="value" value="${escapeHtml(row.command || "")}" placeholder="${escapeHtml(row.id === "打开" ? "例如 打开" : "例如 关闭")}" />
      <div class="cell-text">事件类型</div>
      <div class="cell-text">${row.id === "打开" ? "开启推送" : "关闭推送"}</div>
      <button data-act="save" type="button">保存</button>
    `;
    el.querySelector('[data-act="save"]').addEventListener("click", async () => {
      try {
        await bridge.apiPost("page/commands/save", {
          id: row.id,
          command: el.querySelector('[data-k="value"]').value.trim(),
        });
        setStatus("已保存");
        await loadPush();
      } catch (err) {
        setStatus(err.message || "保存失败", true);
      }
    });
    pushListEl.appendChild(el);
  }
  for (const group of payload.groups || []) {
    const head = document.createElement("div");
    head.className = "group-head";
    head.textContent = group.name;
    pushListEl.appendChild(head);
    for (const event of group.events || []) {
      const el = document.createElement("div");
      el.className = "row";
      el.innerHTML = `
        <div class="cell-text">${escapeHtml(payload.open.command)}</div>
        <input data-k="name" value="${escapeHtml(event.name || "")}" />
        <div class="cell-text">${escapeHtml(event.desc || event.kind)}</div>
        <button data-act="save" type="button">保存</button>
      `;
      el.querySelector('[data-act="save"]').addEventListener("click", async () => {
        try {
          await bridge.apiPost("page/push-commands/save", {
            action: event.action,
            name: el.querySelector('[data-k="name"]').value.trim(),
          });
          setStatus("已保存");
          await loadPush();
        } catch (err) {
          setStatus(err.message || "保存失败", true);
        }
      });
      pushListEl.appendChild(el);
    }
  }
}

function renderServers(payload) {
  const servers = payload.servers || [];
  serverListEl.innerHTML = `<div class="head"><span>正式区服</span><span>别名</span><span></span><span></span></div>`;
  for (const row of servers) {
    const el = document.createElement("div");
    el.className = "row";
    el.innerHTML = `
      <div class="id">${escapeHtml(row.server)}</div>
      <input data-k="aliases" value="${escapeHtml(row.aliases_text || "")}" placeholder="多个别名用逗号分隔" />
      <div></div>
      <button data-act="save" type="button">保存</button>
    `;
    el.querySelector('[data-act="save"]').addEventListener("click", async () => {
      try {
        await bridge.apiPost("page/servers/save", {
          server: row.server,
          aliases: el.querySelector('[data-k="aliases"]').value.trim(),
        });
        setStatus("已保存");
        await loadServers();
      } catch (err) {
        setStatus(err.message || "保存失败", true);
      }
    });
    serverListEl.appendChild(el);
  }
}

async function loadSessions() {
  renderSessions(await bridge.apiGet("page/sessions"));
}

async function loadCommands() {
  renderCommands(await bridge.apiGet("page/commands"));
}

async function loadPush() {
  renderPush(await bridge.apiGet("page/push-commands"));
}

async function loadServers() {
  renderServers(await bridge.apiGet("page/servers"));
}

async function loadCurrent() {
  if (currentView === "commands") return loadCommands();
  if (currentView === "push") return loadPush();
  if (currentView === "servers") return loadServers();
  return loadSessions();
}

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    setView(btn.dataset.view);
    try {
      await loadCurrent();
      setStatus("");
    } catch (err) {
      setStatus(err.message || "加载失败", true);
    }
  });
});

document.getElementById("refreshBtn").addEventListener("click", () => {
  loadCurrent().then(() => setStatus("已刷新")).catch((e) => setStatus(e.message, true));
});

resetBtn.addEventListener("click", async () => {
  try {
    if (currentView === "commands") {
      await bridge.apiPost("page/commands/reset", {});
      setStatus("已恢复默认命令");
      await loadCommands();
      return;
    }
    if (currentView === "push") {
      await bridge.apiPost("page/push-commands/reset", {});
      setStatus("已恢复默认推送命令");
      await loadPush();
      return;
    }
    if (currentView === "servers") {
      await bridge.apiPost("page/servers/reset", {});
      setStatus("已恢复默认别名");
      await loadServers();
    }
  } catch (err) {
    setStatus(err.message || "恢复失败", true);
  }
});

waitForPluginBridge()
  .then((readyBridge) => {
    bridge = readyBridge;
    setView("sessions");
    return loadCurrent();
  })
  .catch((e) => setStatus(e.message, true));
