const statusEl = document.getElementById("status");
const listEl = document.getElementById("list");
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

function render(payload) {
  const commands = payload.commands || [];
  listEl.innerHTML = `<div class="head"><span>功能</span><span>命令</span><span>描述</span><span></span></div>`;
  for (const row of commands) {
    const el = document.createElement("div");
    el.className = "row";
    el.innerHTML = `
      <div class="id">${escapeHtml(row.id)}</div>
      <input data-k="command" value="${escapeHtml(row.command || "")}" />
      <input data-k="desc" value="${escapeHtml(row.desc || "")}" />
      <button data-act="save" type="button">保存</button>
    `;
    el.querySelector('[data-act="save"]').addEventListener("click", async () => {
      try {
        await bridge.apiPost("page/commands/save", {
          id: row.id,
          command: el.querySelector('[data-k="command"]').value.trim(),
          desc: el.querySelector('[data-k="desc"]').value.trim(),
        });
        setStatus("已保存");
        await load();
      } catch (err) {
        setStatus(err.message || "保存失败", true);
      }
    });
    listEl.appendChild(el);
  }
}

async function load() {
  const data = await bridge.apiGet("page/commands");
  render(data);
}

document.getElementById("refreshBtn").addEventListener("click", () => {
  load().then(() => setStatus("已刷新")).catch((e) => setStatus(e.message, true));
});
document.getElementById("resetBtn").addEventListener("click", async () => {
  try {
    await bridge.apiPost("page/commands/reset", {});
    setStatus("已恢复默认命令");
    await load();
  } catch (err) {
    setStatus(err.message || "恢复失败", true);
  }
});

waitForPluginBridge()
  .then((readyBridge) => {
    bridge = readyBridge;
    return load();
  })
  .catch((e) => setStatus(e.message, true));
