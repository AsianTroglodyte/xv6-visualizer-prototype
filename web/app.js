const statusEl = document.getElementById("status");
const terminalEl = document.getElementById("terminal");
const connectButton = document.getElementById("connect");
const disconnectButton = document.getElementById("disconnect");
const interruptButton = document.getElementById("interrupt");
const form = document.getElementById("input-form");
const input = document.getElementById("input");
const sendButton = document.getElementById("send");

let socket = null;

function wsUrl() {
  const host = window.location.hostname || "127.0.0.1";
  const params = new URLSearchParams(window.location.search);
  const port = params.get("ws_port") || "8765";
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${host}:${port}/terminal`;
}

function append(text) {
  terminalEl.textContent += text;
  terminalEl.scrollTop = terminalEl.scrollHeight;
}

function setConnected(connected) {
  connectButton.disabled = connected;
  disconnectButton.disabled = !connected;
  interruptButton.disabled = !connected;
  input.disabled = !connected;
  sendButton.disabled = !connected;
  if (connected) {
    input.focus();
  }
}

function connect() {
  if (socket && socket.readyState !== WebSocket.CLOSED) {
    return;
  }

  terminalEl.textContent = "";
  statusEl.textContent = `Connecting to ${wsUrl()}`;
  connectButton.disabled = true;
  socket = new WebSocket(wsUrl());

  socket.addEventListener("open", () => {
    statusEl.textContent = "Connected";
    setConnected(true);
  });

  socket.addEventListener("message", (event) => {
    append(String(event.data));
  });

  socket.addEventListener("close", () => {
    statusEl.textContent = "Disconnected";
    setConnected(false);
    socket = null;
  });

  socket.addEventListener("error", () => {
    append(`\n[browser] WebSocket error while connecting to ${wsUrl()}\n`);
  });
}

function send(text) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(text);
  }
}

connectButton.addEventListener("click", connect);

disconnectButton.addEventListener("click", () => {
  if (socket) {
    socket.close();
  }
});

interruptButton.addEventListener("click", () => {
  send("\x03");
  input.focus();
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = input.value;
  input.value = "";
  append(`${text}\n`);
  send(`${text}\n`);
});

terminalEl.addEventListener("click", () => input.focus());

append("Starting a fresh xv6/QEMU instance.\n");
setConnected(false);
connect();
