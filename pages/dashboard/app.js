const statusEl = document.getElementById("status");
const globalConfigEl = document.getElementById("globalConfig");
const cardsEl = document.getElementById("cards");
const commandListEl = document.getElementById("commandList");
const pushListEl = document.getElementById("pushList");
const serverListEl = document.getElementById("serverList");
const resetBtn = document.getElementById("resetBtn");
let bridge = null;
let currentView = "global";
const TOKEN_SOURCE_TEXT = {
  none: "未配置",
  global: "已配置全局",
  group: "已配置群属",
};

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

function sourcePill(label, labelClass, state) {
  const sourceState = state || "none";
  const statusText = TOKEN_SOURCE_TEXT[sourceState] || TOKEN_SOURCE_TEXT.none;
  return `
    <span class="pill source-pill source-${escapeHtml(sourceState)}">
      <span class="source-label ${escapeHtml(labelClass)}">${escapeHtml(label)}：</span>
      <span class="source-status status-${escapeHtml(sourceState)}">${escapeHtml(statusText)}</span>
    </span>
  `;
}

function groupCredentialAction(item) {
  return `
    <div class="credential-actions">
      <button
        data-act="credential-delete"
        data-kind="${escapeHtml(item.kind || "")}"
        data-value="${escapeHtml(item.value || "")}"
        class="ghost"
        type="button"
      >移除</button>
    </div>
  `;
}

function credentialPool(title, items, emptyText, removed = false, itemAction = "") {
  const rows = (items || []).map((item) => `
    <div class="credential-item${removed ? " removed" : ""}">
      <code>${escapeHtml(item.value || "")}</code>
      <div class="credential-meta">
        ${escapeHtml(item.failure_reason || (removed ? "失效" : "可用"))}
        ${escapeHtml(item.removed_at || item.updated_at || "")}
      </div>
      ${itemAction ? itemAction(item) : ""}
    </div>
  `).join("");
  return `
    <div class="credential-pool${removed ? " removed-pool" : ""}">
      <div class="pool-title">${escapeHtml(title)}</div>
      <div class="pool-items">${rows || `<div class="credential-empty">${escapeHtml(emptyText)}</div>`}</div>
    </div>
  `;
}

function globalCredentialItem(item, kind) {
  const failed = item.status === "removed";
  const state = failed ? "失效" : "可用";
  const reason = item.failure_reason || "";
  const time = failed ? item.removed_at : item.updated_at;
  return `
    <div class="credential-item${failed ? " removed" : ""}">
      <code>${escapeHtml(item.value || "")}</code>
      <div class="credential-meta">
        ${escapeHtml(state)}${reason ? ` · ${escapeHtml(reason)}` : ""}${time ? ` · ${escapeHtml(time)}` : ""}
      </div>
      <div class="credential-actions">
        <button data-act="global-delete" data-id="${escapeHtml(item.id)}" data-kind="${escapeHtml(kind)}" class="ghost" type="button">移除</button>
      </div>
    </div>
  `;
}

function renderGlobalCredentials(payload) {
  const tokens = payload.tokens || [];
  const removedTokens = payload.removed_tokens || [];
  const pushTokens = payload.push_tokens || [];
  const removedPushTokens = payload.removed_push_tokens || [];
  const tickets = payload.tickets || [];
  const config = payload.config || {};
  globalConfigEl.innerHTML = `
    <article class="card global-card">
      <div class="card-head">
        <div>
          <h2 class="card-title">全局配置</h2>
          <p class="umo">统一维护 JX3API 连接、凭据池与指令前缀。</p>
        </div>
      </div>
      <div class="rows">
        <div class="row">
          <label class="field">
            <span>JX3API 基础地址</span>
            <input data-k="jx3api_base_url" value="${escapeHtml(config.jx3api_base_url || "")}" />
          </label>
        </div>
        <div class="row">
          <label class="field">
            <span>添加全局接口令牌</span>
            <input data-k="global-token" placeholder="一次添加一条" />
          </label>
          <div class="row-actions">
            <button data-act="global-token" type="button">添加令牌</button>
          </div>
        </div>
        <div class="credential-pool">
          <div class="pool-title">全局接口令牌 · 可用池</div>
          <div class="pool-items">
            ${tokens.map((item) => globalCredentialItem(item, "token")).join("") || `<div class="credential-empty">未配置</div>`}
          </div>
        </div>
        <div class="credential-pool removed-pool">
          <div class="pool-title">全局接口令牌 · 失效池</div>
          <div class="pool-items">
            ${removedTokens.map((item) => globalCredentialItem(item, "token")).join("") || `<div class="credential-empty">暂无</div>`}
          </div>
        </div>
        <div class="row">
          <label class="field">
            <span>JX3API 事件通道地址</span>
            <input data-k="jx3api_ws_url" value="${escapeHtml(config.jx3api_ws_url || "")}" />
          </label>
        </div>
        <div class="row">
          <label class="field">
            <span>添加全局推送令牌</span>
            <input data-k="global-push-token" placeholder="一次添加一条" />
          </label>
          <div class="row-actions">
            <button data-act="global-push-token" type="button">添加令牌</button>
          </div>
        </div>
        <div class="credential-pool">
          <div class="pool-title">全局推送令牌 · 可用池</div>
          <div class="pool-items">
            ${pushTokens.map((item) => globalCredentialItem(item, "push_token")).join("") || `<div class="credential-empty">未配置</div>`}
          </div>
        </div>
        <div class="credential-pool removed-pool">
          <div class="pool-title">全局推送令牌 · 失效池</div>
          <div class="pool-items">
            ${removedPushTokens.map((item) => globalCredentialItem(item, "push_token")).join("") || `<div class="credential-empty">暂无</div>`}
          </div>
        </div>
        <div class="row">
          <label class="field">
            <span>添加全局推栏标识</span>
            <input data-k="global-ticket" placeholder="一次添加一条" />
          </label>
          <div class="row-actions">
            <button data-act="global-ticket" type="button">添加推栏</button>
          </div>
        </div>
        <div class="credential-pool">
          <div class="pool-title">全局推栏标识 · 可用池</div>
          <div class="pool-items">
            ${tickets.map((item) => globalCredentialItem(item, "ticket")).join("") || `<div class="credential-empty">未配置</div>`}
          </div>
        </div>
        <div class="switches">
          <label class="toggle">
            <input data-k="jx3api_ssl_verify" type="checkbox" ${config.jx3api_ssl_verify ? "checked" : ""} />
            校验 JX3API 接口 TLS 证书
          </label>
          <label class="toggle">
            <input data-k="prefix_enable" type="checkbox" ${config.prefix_enable ? "checked" : ""} />
            启用插件指令前缀
          </label>
        </div>
        <div class="row">
          <label class="field">
            <span>插件指令前缀</span>
            <input data-k="prefix_text" value="${escapeHtml(config.prefix_text || "")}" />
          </label>
          <div class="row-actions">
            <button data-act="global-save" type="button">保存全局配置</button>
          </div>
        </div>
      </div>
    </article>
  `;
}

function setView(view) {
  currentView = view;
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === view);
  });
  document.querySelectorAll(".view-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.viewPanel === view);
  });
  resetBtn.hidden = !["commands", "push", "servers"].includes(view);
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
  const groups = new Map();
  for (const row of sessions) {
    const isAdmin = row.claim_type === "astrbot_admin" || !row.claim_identity;
    const key = isAdmin ? "astrbot_admin" : `claimant:${row.claim_identity}`;
    const title = isAdmin ? "AstrBot 管理员" : (row.claim_name || row.claim_identity || "未认领");
    if (!groups.has(key)) groups.set(key, { title, sessions: [] });
    groups.get(key).sessions.push(row);
  }
  const orderedGroups = [...groups.values()].sort((left, right) => {
    if (left.title === "AstrBot 管理员") return -1;
    if (right.title === "AstrBot 管理员") return 1;
    return left.title.localeCompare(right.title, "zh-CN");
  });
  for (const group of orderedGroups) {
    const head = document.createElement("div");
    head.className = "group-head";
    head.textContent = group.title;
    cardsEl.appendChild(head);
    for (const row of group.sessions) {
      cardsEl.appendChild(sessionCard(row));
    }
  }
}

function sessionCard(row) {
  const ticketSource = (row.tickets || []).length ? "group" : row.has_ticket ? "global" : "none";
  const card = document.createElement("article");
  card.className = "card";
  card.innerHTML = `
    <div class="card-head">
      <div>
        <h2 class="card-title">${escapeHtml(row.display_name || "未命名会话")}</h2>
        <p class="umo">${escapeHtml(row.umo || "")}</p>
      </div>
      <div class="pills">
        ${pill(row.claim_type === "astrbot_admin" || !row.claim_identity ? "AstrBot 管理员" : `认领人 ${row.claim_name || row.claim_identity}`, true)}
        ${pill(row.server || "未绑定区服", Boolean(row.server))}
        ${sourcePill("接口令牌", "label-token", row.token_source || "none")}
        ${sourcePill("推送令牌", "label-push-token", row.push_token_source || "none")}
        ${sourcePill("推栏", "label-ticket", ticketSource)}
        ${pill(row.bot_enabled === false ? "机器人已关闭" : "机器人开启", row.bot_enabled !== false)}
        ${pill(
          row.push_fail_count ? `推送异常 ${row.push_fail_count} 次` : "推送正常",
          !row.push_fail_count,
          row.push_last_error || ""
        )}
      </div>
    </div>
    <div class="quick-actions">
      <button data-act="delete" class="danger" type="button">删除会话</button>
      ${row.claim_type === "claimant" && row.claim_identity ? `<button data-act="clear-claim" class="ghost" type="button">取消认领</button>` : ""}
    </div>
    <div class="switches">
      <label class="toggle">
        <input data-k="bot_enabled" type="checkbox" ${row.bot_enabled === false ? "" : "checked"} />
        启用该会话机器人
      </label>
      <label class="toggle">
        <input data-k="use_global_token" type="checkbox" ${(row.tokens || []).length ? "disabled" : ""} ${row.use_global_token ? "checked" : ""} />
        使用全局接口令牌
      </label>
      <label class="toggle">
        <input data-k="use_global_push_token" type="checkbox" ${(row.push_tokens || []).length ? "disabled" : ""} ${row.use_global_push_token ? "checked" : ""} />
        使用全局推送令牌
      </label>
      <label class="toggle">
        <input data-k="use_global_ticket" type="checkbox" ${(row.tickets || []).length ? "disabled" : ""} ${row.use_global_ticket ? "checked" : ""} />
        使用全局推栏标识
      </label>
    </div>
    <div class="rows">
      <div class="row">
        <label class="field">
          <span>添加接口令牌</span>
          <input data-k="token" data-initial="" value="" placeholder="一次添加一条" />
        </label>
        <div class="row-actions">
          <button data-act="token" type="button">添加令牌</button>
        </div>
      </div>
      <div class="row">
        <label class="field">
          <span>添加推送令牌</span>
          <input data-k="push-token" data-initial="" value="" placeholder="一次添加一条" />
        </label>
        <div class="row-actions">
          <button data-act="push-token" type="button">添加推送</button>
        </div>
      </div>
      <div class="row">
        <label class="field">
          <span>添加推栏标识</span>
          <input data-k="ticket" data-initial="" value="" placeholder="一次添加一条" />
        </label>
        <div class="row-actions">
          <button data-act="ticket" type="button">添加推栏</button>
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
      ${(row.tokens || []).length ? credentialPool("群属接口令牌 · 可用池", row.tokens, "暂无", false, groupCredentialAction) : ""}
      ${(row.push_tokens || []).length ? credentialPool("群属推送令牌 · 可用池", row.push_tokens, "暂无", false, groupCredentialAction) : ""}
      ${(row.tickets || []).length ? credentialPool("群属推栏标识 · 可用池", row.tickets, "暂无", false, groupCredentialAction) : ""}
      ${(row.removed_tokens || []).length ? credentialPool("群属接口令牌 · 失效池", row.removed_tokens, "暂无", true, groupCredentialAction) : ""}
      ${(row.removed_push_tokens || []).length ? credentialPool("群属推送令牌 · 失效池", row.removed_push_tokens, "暂无", true, groupCredentialAction) : ""}
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
    const token = card.querySelector('[data-k="token"]').value.trim();
    const pushToken = card.querySelector('[data-k="push-token"]').value.trim();
    const ticket = card.querySelector('[data-k="ticket"]').value.trim();
    const managerEl = card.querySelector('[data-k="managers"]');
    const managers = managerEl ? managerEl.value.trim() : "";
    if (act === "token") {
      if (!row.umo || !token) return setStatus("请填写接口令牌", true);
      if (token === (card.querySelector('[data-k="token"]').dataset.initial || "")) {
        return setStatus("接口令牌未修改，保持当前配置");
      }
      await run(() => bridge.apiPost("page/sessions/token", { umo: row.umo, token }));
    } else if (act === "push-token") {
      if (!row.umo || !pushToken) return setStatus("请填写推送令牌", true);
      await run(() => bridge.apiPost("page/sessions/push-token", { umo: row.umo, token: pushToken }));
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
    } else if (act === "credential-delete") {
      const kind = btn.dataset.kind;
      const value = btn.dataset.value;
      if (!row.umo || !kind || !value) return setStatus("缺少移除凭据信息", true);
      await run(() => bridge.apiPost("page/sessions/credential/delete", {
        umo: row.umo,
        kind,
        value,
      }));
    } else if (act === "delete") {
      if (btn.dataset.armed !== "true") {
        btn.dataset.armed = "true";
        btn.textContent = "再次点击删除";
        setStatus("再次点击“删除会话”确认清理。", true);
        window.setTimeout(() => {
          if (!document.contains(btn) || btn.dataset.armed !== "true") return;
          btn.dataset.armed = "";
          btn.textContent = "删除会话";
          setStatus("已取消删除。");
        }, 5000);
        return;
      }
      try {
        const result = await bridge.apiPost("page/sessions/delete", { umo: row.umo });
        setStatus(result.message || "已删除会话", !result.left);
        await loadSessions();
      } catch (err) {
        setStatus(err.message || "删除失败", true);
      }
    }
  });

  for (const kind of ["token", "push_token", "ticket"]) {
    card.querySelector(`[data-k="use_global_${kind === "token" ? "token" : kind}"]`).addEventListener("change", async (ev) => {
    const enabled = ev.target.checked;
    try {
      if (!row.umo) throw new Error("当前会话缺少标识");
      await bridge.apiPost("page/sessions/use-global", { umo: row.umo, enabled, kind });
      setStatus(enabled ? "已启用全局凭据回退" : "已关闭全局凭据回退");
      await loadSessions();
    } catch (err) {
      ev.target.checked = !enabled;
      setStatus(err.message || "保存失败", true);
    }
    });
  }
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

async function loadGlobalCredentials() {
  const [credentialPayload, configPayload] = await Promise.all([
    bridge.apiGet("page/credentials"),
    bridge.apiGet("page/global-config"),
  ]);
  renderGlobalCredentials({ ...credentialPayload, config: configPayload.config });
}

globalConfigEl.addEventListener("click", async (ev) => {
  const btn = ev.target.closest("button");
  if (!btn) return;
  const act = btn.dataset.act;
  try {
    if (act === "global-token" || act === "global-push-token" || act === "global-ticket") {
      const input = globalConfigEl.querySelector(`[data-k="${act}"]`);
      const value = (input?.value || "").trim();
      const labels = {
        "global-token": "全局接口令牌",
        "global-push-token": "全局推送令牌",
        "global-ticket": "全局推栏标识",
      };
      if (!value) throw new Error(`请填写${labels[act]}`);
      await bridge.apiPost("page/credentials/add", {
        kind: act === "global-token" ? "token" : act === "global-push-token" ? "push_token" : "ticket",
        value,
      });
      if (input) input.value = "";
      setStatus("已保存");
      await loadGlobalCredentials();
    } else if (act === "global-save") {
      const value = (key) => globalConfigEl.querySelector(`[data-k="${key}"]`)?.value ?? "";
      const checked = (key) => Boolean(globalConfigEl.querySelector(`[data-k="${key}"]`)?.checked);
      await bridge.apiPost("page/global-config/save", {
        jx3api_base_url: value("jx3api_base_url"),
        jx3api_ws_url: value("jx3api_ws_url"),
        jx3api_ssl_verify: checked("jx3api_ssl_verify"),
        prefix_enable: checked("prefix_enable"),
        prefix_text: value("prefix_text"),
      });
      setStatus("全局配置已保存");
      await loadGlobalCredentials();
    } else if (act === "global-delete") {
      await bridge.apiPost("page/credentials/delete", { id: Number(btn.dataset.id) });
      setStatus("已移除全局凭据");
      await loadGlobalCredentials();
    }
  } catch (err) {
    setStatus(err.message || "保存失败", true);
  }
});

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
  if (currentView === "global") return loadGlobalCredentials();
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
    setView("global");
    return loadCurrent();
  })
  .catch((e) => setStatus(e.message, true));
