const state = {
  sessionId: null,
  docId: null,
  isUploading: false,
  isWaiting: false,
  approvalPollId: null,
  isListening: false,
};

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

const elements = {
  chatForm: document.querySelector("#chat-form"),
  chatSection: document.querySelector("#chat-section"),
  changeDocument: document.querySelector("#change-document"),
  documentName: document.querySelector("#document-name"),
  dropZone: document.querySelector("#drop-zone"),
  fileInput: document.querySelector("#pdf-file"),
  messages: document.querySelector("#messages"),
  question: document.querySelector("#question"),
  sendButton: document.querySelector("#send-button"),
  uploadSection: document.querySelector("#upload-section"),
  uploadStatus: document.querySelector("#upload-status"),
  voiceButton: document.querySelector("#voice-button"),
  voiceStatus: document.querySelector("#voice-status"),
};

let recognition = null;
let voiceShouldSubmit = false;

async function createSession() {
  const response = await fetch("/session");
  if (!response.ok) throw new Error("Could not connect to the backend.");
  const data = await response.json();
  state.sessionId = data.session_id;
}

function setUploadStatus(message = "", type = "") {
  elements.uploadStatus.textContent = message;
  elements.uploadStatus.className = `status ${type}`;
}

function appendInlineMarkdown(parent, value) {
  const text = value.replace(/\\([\\`*_~])/g, "$1");
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`|<br\s*\/?\s*>)/gi;
  let lastIndex = 0;

  for (const match of text.matchAll(pattern)) {
    parent.append(document.createTextNode(text.slice(lastIndex, match.index)));
    const token = match[0];
    if (token.startsWith("**")) {
      const strong = document.createElement("strong");
      strong.textContent = token.slice(2, -2);
      parent.append(strong);
    } else if (token.startsWith("`")) {
      const code = document.createElement("code");
      code.textContent = token.slice(1, -1);
      parent.append(code);
    } else {
      parent.append(document.createElement("br"));
    }
    lastIndex = match.index + token.length;
  }
  parent.append(document.createTextNode(text.slice(lastIndex)));
}

function tableCells(line) {
  return line.trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim());
}

function isTableSeparator(line) {
  const cells = tableCells(line);
  return cells.length > 1 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function normalizeWrappedTables(markdown) {
  const source = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
  const normalized = [];

  for (let index = 0; index < source.length;) {
    if (!source[index].includes("|")) {
      normalized.push(source[index]);
      index += 1;
      continue;
    }

    let separatorStart = -1;
    for (let cursor = index + 1; cursor < Math.min(source.length, index + 7); cursor += 1) {
      const candidate = source[cursor].trim();
      if (/^[|:\-\s]+$/.test(candidate) && candidate.includes("---")) {
        separatorStart = cursor;
        break;
      }
      if (candidate && !candidate.includes("|")) break;
    }
    if (separatorStart < 0) {
      normalized.push(source[index]);
      index += 1;
      continue;
    }

    const header = source.slice(index, separatorStart).join(" ").replace(/\|\s+\|/g, "|");
    const columnCount = tableCells(header).length;
    if (columnCount < 2) {
      normalized.push(source[index]);
      index += 1;
      continue;
    }

    let bodyStart = separatorStart;
    while (bodyStart < source.length && /^[|:\-\s]+$/.test(source[bodyStart].trim())) {
      bodyStart += 1;
    }
    normalized.push(header, `| ${Array(columnCount).fill("---").join(" | ")} |`);

    let rowParts = [];
    let cursor = bodyStart;
    while (cursor < source.length && source[cursor].trim() && source[cursor].includes("|")) {
      rowParts.push(source[cursor].trim());
      const combined = rowParts.join(" ").replace(/\|\s+\|/g, "|");
      if ((combined.match(/\|/g) || []).length >= columnCount + 1) {
        normalized.push(combined);
        rowParts = [];
      }
      cursor += 1;
    }
    if (rowParts.length) normalized.push(rowParts.join(" "));
    index = cursor;
  }
  return normalized;
}

function isBlockStart(lines, index) {
  const line = lines[index] || "";
  return (
    /^#{1,3}\s+/.test(line)
    || /^\s*(?:[-*]|\d+\.)\s+/.test(line)
    || (line.includes("|") && isTableSeparator(lines[index + 1] || ""))
  );
}

function renderMarkdown(container, markdown) {
  container.replaceChildren();
  const lines = normalizeWrappedTables(markdown);

  for (let index = 0; index < lines.length;) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      const node = document.createElement(`h${heading[1].length + 2}`);
      appendInlineMarkdown(node, heading[2]);
      container.append(node);
      index += 1;
      continue;
    }

    if (line.includes("|") && isTableSeparator(lines[index + 1] || "")) {
      const wrapper = document.createElement("div");
      wrapper.className = "markdown-table-wrapper";
      const table = document.createElement("table");
      const head = document.createElement("thead");
      const headRow = document.createElement("tr");
      tableCells(line).forEach((cell) => {
        const th = document.createElement("th");
        appendInlineMarkdown(th, cell);
        headRow.append(th);
      });
      head.append(headRow);
      table.append(head);

      const body = document.createElement("tbody");
      index += 2;
      while (index < lines.length && lines[index].includes("|") && lines[index].trim()) {
        const row = document.createElement("tr");
        tableCells(lines[index]).forEach((cell) => {
          const td = document.createElement("td");
          appendInlineMarkdown(td, cell);
          row.append(td);
        });
        body.append(row);
        index += 1;
      }
      table.append(body);
      wrapper.append(table);
      container.append(wrapper);
      continue;
    }

    const listMatch = line.match(/^\s*([-*]|\d+\.)\s+(.+)$/);
    if (listMatch) {
      const ordered = /\d+\./.test(listMatch[1]);
      const list = document.createElement(ordered ? "ol" : "ul");
      while (index < lines.length) {
        const item = lines[index].match(/^\s*([-*]|\d+\.)\s+(.+)$/);
        if (!item || /\d+\./.test(item[1]) !== ordered) break;
        const li = document.createElement("li");
        appendInlineMarkdown(li, item[2]);
        list.append(li);
        index += 1;
      }
      container.append(list);
      continue;
    }

    const paragraphLines = [line.trim()];
    index += 1;
    while (index < lines.length && lines[index].trim() && !isBlockStart(lines, index)) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    const paragraph = document.createElement("p");
    appendInlineMarkdown(paragraph, paragraphLines.join(" "));
    container.append(paragraph);
  }
}

function addMessage(role, text, extraClass = "") {
  const message = document.createElement("div");
  message.className = `message ${role} ${extraClass}`;
  if (role === "assistant" && !extraClass.includes("typing")) {
    renderMarkdown(message, text);
  } else {
    message.textContent = text;
  }
  elements.messages.append(message);
  elements.messages.scrollTop = elements.messages.scrollHeight;
  return message;
}

function setChatEnabled(enabled) {
  elements.question.disabled = !enabled;
  elements.sendButton.disabled = !enabled;
  elements.voiceButton.disabled = !enabled || !SpeechRecognition;
}

function setVoiceState(listening, message = "") {
  state.isListening = listening;
  elements.voiceButton.classList.toggle("listening", listening);
  elements.voiceButton.setAttribute("aria-label", listening ? "Stop listening" : "Start voice command");
  elements.voiceButton.title = listening ? "Stop listening" : "Speak your question";
  elements.voiceStatus.textContent = message;
}

function setupVoiceRecognition() {
  if (!SpeechRecognition) {
    elements.voiceButton.disabled = true;
    elements.voiceButton.title = "Voice commands are not supported in this browser";
    elements.voiceStatus.textContent = "Voice commands work in supported Chrome, Edge, and Safari browsers.";
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = navigator.language || "en-US";
  recognition.continuous = false;
  recognition.interimResults = true;

  recognition.addEventListener("start", () => setVoiceState(true, "Listening… speak your command."));
  recognition.addEventListener("result", (event) => {
    let transcript = "";
    let isFinal = false;
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      transcript += event.results[index][0].transcript;
      isFinal ||= event.results[index].isFinal;
    }
    elements.question.value = transcript.trim();
    voiceShouldSubmit = isFinal && Boolean(elements.question.value);
    elements.voiceStatus.textContent = isFinal ? "Command captured. Sending…" : "Listening…";
  });
  recognition.addEventListener("error", (event) => {
    voiceShouldSubmit = false;
    const messages = {
      "not-allowed": "Microphone access was blocked. Allow it in your browser settings.",
      "no-speech": "No speech was detected. Please try again.",
      "audio-capture": "No microphone was found.",
    };
    setVoiceState(false, messages[event.error] || "Voice recognition stopped. Please try again.");
  });
  recognition.addEventListener("end", () => {
    const shouldSubmit = voiceShouldSubmit;
    voiceShouldSubmit = false;
    setVoiceState(false, shouldSubmit ? "" : elements.voiceStatus.textContent);
    if (shouldSubmit && !state.isWaiting) elements.chatForm.requestSubmit();
  });

  elements.voiceButton.addEventListener("click", () => {
    if (state.isListening) {
      voiceShouldSubmit = false;
      recognition.stop();
      return;
    }
    elements.question.value = "";
    elements.voiceStatus.textContent = "";
    try {
      recognition.start();
    } catch (_) {
      setVoiceState(false, "Could not start the microphone. Please try again.");
    }
  });
}

function stopApprovalPolling() {
  if (state.approvalPollId !== null) {
    window.clearInterval(state.approvalPollId);
    state.approvalPollId = null;
  }
}

function startApprovalPolling() {
  stopApprovalPolling();
  const startedAt = Date.now();

  state.approvalPollId = window.setInterval(async () => {
    if (!state.sessionId || Date.now() - startedAt > 60 * 60 * 1000) {
      stopApprovalPolling();
      return;
    }

    try {
      const response = await fetch(`/chat/status/${encodeURIComponent(state.sessionId)}`);
      if (!response.ok) return;
      const result = await response.json();
      if (["completed", "rejected", "failed"].includes(result.status)) {
        stopApprovalPolling();
        addMessage("assistant", result.answer || "Email approval was processed.");
      }
    } catch (_) {
      // A temporary polling failure should not interrupt the chat experience.
    }
  }, 3000);
}

async function uploadPdfs(fileList) {
  const files = Array.from(fileList || []);
  if (!files.length || state.isUploading) return;
  const invalidFile = files.find(
    (file) => file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf"),
  );
  if (invalidFile) {
    setUploadStatus(`Only PDF files are supported (${invalidFile.name}).`, "error");
    return;
  }

  state.isUploading = true;
  setUploadStatus(`Uploading and preparing ${files.length} PDF${files.length === 1 ? "" : "s"}…`);
  const data = new FormData();
  files.forEach((file) => data.append("files", file));

  try {
    const response = await fetch("/upload", { method: "POST", body: data });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || !result.doc_id) {
      throw new Error(result.detail || result.error || "The document could not be processed.");
    }

    state.docId = result.doc_id;
    elements.documentName.textContent = files.map((file) => file.name).join(", ");
    elements.uploadSection.hidden = true;
    elements.chatSection.hidden = false;
    elements.messages.replaceChildren();
    addMessage(
      "assistant",
      `${files.length} PDF${files.length === 1 ? " is" : "s are"} ready. What would you like to know?`,
    );
    elements.question.focus();
  } catch (error) {
    setUploadStatus(error.message || "Upload failed. Please try again.", "error");
  } finally {
    state.isUploading = false;
  }
}

async function sendQuestion(event) {
  event.preventDefault();
  const query = elements.question.value.trim();
  if (!query || state.isWaiting || !state.docId) return;

  addMessage("user", query);
  elements.question.value = "";
  state.isWaiting = true;
  setChatEnabled(false);
  const typing = addMessage("assistant", "Thinking…", "typing");

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        doc_id: state.docId,
        session_id: state.sessionId,
        document_name: elements.documentName.textContent,
      }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || !result.answer) {
      throw new Error(result.detail || "The backend could not answer this question.");
    }
    renderMarkdown(typing, result.answer);
    typing.classList.remove("typing");
    if (result.requires_approval) {
      startApprovalPolling();
    }
  } catch (error) {
    typing.textContent = error.message || "Something went wrong. Please try again.";
    typing.classList.remove("typing");
  } finally {
    state.isWaiting = false;
    setChatEnabled(true);
    elements.question.focus();
  }
}

function resetDocument() {
  stopApprovalPolling();
  if (state.isListening && recognition) recognition.abort();
  state.docId = null;
  elements.fileInput.value = "";
  elements.chatSection.hidden = true;
  elements.uploadSection.hidden = false;
  setUploadStatus();
  createSession().catch((error) => setUploadStatus(error.message, "error"));
}

elements.fileInput.addEventListener("change", (event) => uploadPdfs(event.target.files));
elements.chatForm.addEventListener("submit", sendQuestion);
elements.changeDocument.addEventListener("click", resetDocument);

["dragenter", "dragover"].forEach((eventName) => {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.add("dragging");
  });
});
["dragleave", "drop"].forEach((eventName) => {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove("dragging");
  });
});
elements.dropZone.addEventListener("drop", (event) => uploadPdfs(event.dataTransfer.files));

setupVoiceRecognition();
createSession().catch((error) => setUploadStatus(error.message, "error"));
