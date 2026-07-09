const terminal = document.getElementById("terminal");
const form = document.getElementById("command-form");
const input = document.getElementById("command-input");
const backendBadge = document.getElementById("backend-badge");
const assetBadge = document.getElementById("asset-badge");

const state = {
  backend: "stub",
  prompt: "$",
};

function appendLine(text, cls = "") {
  const div = document.createElement("div");
  div.className = `line ${cls}`.trim();
  div.textContent = text;
  terminal.appendChild(div);
  terminal.scrollTop = terminal.scrollHeight;
}

function appendPromptLine(text) {
  appendLine(`${state.prompt} ${text}`, "accent");
}

function setStatus() {
  backendBadge.textContent = `backend: ${state.backend}`;
  assetBadge.textContent = "assets: staged for wasm QEMU";
}

function bootMessage() {
  appendLine("xv6 browser terminal scaffold", "accent");
  appendLine("This page is ready for a future wasm-QEMU backend.");
  appendLine("For now it behaves like a local terminal UI and records commands.");
  appendLine("When the emulator backend is wired up, commands will be forwarded to stdin.");
  appendLine("");
  appendLine("Try typing a command below. The frontend will echo it back.");
}

function runStubCommand(command) {
  const trimmed = command.trim();
  if (!trimmed) {
    return;
  }

  appendPromptLine(trimmed);

  if (trimmed === "help") {
    appendLine("Available stub commands: help, clear, status");
    return;
  }

  if (trimmed === "clear") {
    terminal.innerHTML = "";
    bootMessage();
    return;
  }

  if (trimmed === "status") {
    appendLine("backend: stub");
    appendLine("next step: connect to wasm QEMU");
    return;
  }

  appendLine(`echo: ${trimmed}`);
  appendLine("This is a frontend-only placeholder until QEMU-in-wasm is attached.");
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  runStubCommand(input.value);
  input.value = "";
  input.focus();
});

terminal.addEventListener("click", () => input.focus());

setStatus();
bootMessage();
input.focus();
