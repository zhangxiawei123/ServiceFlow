const conversation = document.querySelector("#conversation");
const messages = document.querySelector("#messages");
const welcome = document.querySelector("#welcome");
const composer = document.querySelector("#composer");
const input = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const newChatButton = document.querySelector("#new-chat");
const template = document.querySelector("#message-template");
const statusDot = document.querySelector("#status-dot");
const statusText = document.querySelector("#status-text");
const conversationLabel = document.querySelector("#conversation-label");
const sidebar = document.querySelector("#sidebar");
const menuButton = document.querySelector("#menu-button");
const scrim = document.querySelector("#scrim");

const state = {
  busy: false,
  convId: null,
  userId: getUserId(),
};

function getUserId() {
  const stored = localStorage.getItem("echomind-user-id");
  if (stored) return stored;
  const id = `web-${crypto.randomUUID()}`;
  localStorage.setItem("echomind-user-id", id);
  return id;
}

function setServiceState(mode, text) {
  statusDot.className = `status-dot ${mode}`;
  statusText.textContent = text;
}

async function checkHealth() {
  try {
    const response = await fetch("/health", { headers: { Accept: "application/json" } });
    if (response.status === 401) {
      window.location.replace("/");
      return;
    }
    if (!response.ok) throw new Error("service unavailable");
    const payload = await response.json();
    const models = Object.values(payload.agents || {}).map((agent) => agent.model).filter(Boolean);
    const model = models[0] || "服务正常";
    setServiceState("online", `服务在线 · ${model}`);
  } catch {
    setServiceState("offline", "服务暂不可用");
  }
}

function resizeInput() {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    conversation.scrollTop = conversation.scrollHeight;
  });
}

function hideWelcome() {
  welcome.hidden = true;
  messages.style.display = "block";
}

function createMessage(role, body, metadata = null) {
  hideWelcome();
  const fragment = template.content.cloneNode(true);
  const article = fragment.querySelector(".message");
  const avatar = fragment.querySelector(".avatar");
  const roleLabel = fragment.querySelector(".message-role");
  const bodyNode = fragment.querySelector(".message-body");
  const metaNode = fragment.querySelector(".message-meta");

  article.classList.add(role);
  avatar.textContent = role === "user" ? "你" : role === "error" ? "!" : "E";
  roleLabel.textContent = role === "user" ? "你" : role === "error" ? "连接提示" : "EchoMind";
  bodyNode.textContent = body;

  if (metadata) renderMetadata(metaNode, metadata);
  messages.appendChild(fragment);
  scrollToBottom();
  return messages.lastElementChild;
}

function addChip(container, text, accent = false) {
  if (!text) return;
  const chip = document.createElement("span");
  chip.className = `meta-chip${accent ? " accent" : ""}`;
  chip.textContent = text;
  container.appendChild(chip);
}

function renderMetadata(container, data) {
  addChip(container, `Agent · ${data.primary_agent || data.agent_type}`, true);
  addChip(container, `意图 · ${data.intent}`);
  addChip(container, `${Math.round(data.latency_ms)} ms`);
  if (data.knowledge_used) addChip(container, "已检索知识库", true);
  for (const tool of data.tools_used || []) addChip(container, `工具 · ${tool}`);

  if (data.request_id) {
    const details = document.createElement("details");
    details.className = "trace-details";
    const summary = document.createElement("summary");
    summary.textContent = `请求追踪 · ${data.request_id}`;
    const output = document.createElement("pre");
    output.textContent = "展开后加载追踪信息…";
    details.append(summary, output);
    details.addEventListener("toggle", async () => {
      if (!details.open || details.dataset.loaded) return;
      details.dataset.loaded = "true";
      try {
        const response = await fetch(`/trace/tool/${encodeURIComponent(data.request_id)}`);
        const payload = await response.json();
        output.textContent = payload.found ? JSON.stringify(payload.trace, null, 2) : "本次请求没有工具追踪记录。";
      } catch {
        output.textContent = "追踪信息加载失败。";
      }
    });
    container.appendChild(details);
  }
}

function createTypingMessage() {
  const node = createMessage("assistant", "");
  const body = node.querySelector(".message-body");
  body.setAttribute("aria-label", "EchoMind 正在思考");
  body.innerHTML = '<div class="typing" aria-hidden="true"><span></span><span></span><span></span></div>';
  return node;
}

function setBusy(value) {
  state.busy = value;
  input.disabled = value;
  sendButton.disabled = value || !input.value.trim();
}

async function sendMessage(message) {
  const cleanMessage = message.trim();
  if (!cleanMessage || state.busy) return;

  createMessage("user", cleanMessage);
  if (!state.convId) conversationLabel.textContent = cleanMessage;
  input.value = "";
  resizeInput();
  setBusy(true);
  const typing = createTypingMessage();

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        message: cleanMessage,
        user_id: state.userId,
        conv_id: state.convId,
      }),
    });

    let payload;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    if (!response.ok) {
      const detail = payload?.detail || `服务返回 ${response.status}`;
      throw new Error(detail);
    }

    state.convId = payload.conv_id;
    typing.remove();
    createMessage("assistant", payload.response, payload);
  } catch (error) {
    typing.remove();
    createMessage("error", `消息发送失败：${error.message || "请稍后再试"}`);
    checkHealth();
  } finally {
    setBusy(false);
    input.focus();
  }
}

function resetConversation() {
  state.convId = null;
  messages.replaceChildren();
  messages.style.display = "none";
  welcome.hidden = false;
  conversationLabel.textContent = "新对话";
  input.value = "";
  resizeInput();
  setBusy(false);
  closeSidebar();
  input.focus();
}

function openSidebar() {
  sidebar.classList.add("open");
  scrim.classList.add("open");
  menuButton.setAttribute("aria-expanded", "true");
}

function closeSidebar() {
  sidebar.classList.remove("open");
  scrim.classList.remove("open");
  menuButton.setAttribute("aria-expanded", "false");
}

composer.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(input.value);
});

input.addEventListener("input", () => {
  resizeInput();
  sendButton.disabled = state.busy || !input.value.trim();
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    composer.requestSubmit();
  }
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    const prompt = button.dataset.prompt;
    closeSidebar();
    sendMessage(prompt);
  });
});

newChatButton.addEventListener("click", resetConversation);
menuButton.addEventListener("click", () => sidebar.classList.contains("open") ? closeSidebar() : openSidebar());
scrim.addEventListener("click", closeSidebar);
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeSidebar();
});

sendButton.disabled = true;
checkHealth();
setInterval(checkHealth, 30000);
input.focus();
