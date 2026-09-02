const state = {
  sessionId: null,
  docId: null,
  isUploading: false,
  isWaiting: false,
};

const elements = {
  chatForm: document.querySelector("#chat-form"),
  chatSection: document.querySelector("#chat-section"),
  changeDocument: document.querySelector("#change-document"),
  emailSummary: document.querySelector("#email-summary"),
  documentName: document.querySelector("#document-name"),
  dropZone: document.querySelector("#drop-zone"),
  fileInput: document.querySelector("#pdf-file"),
  messages: document.querySelector("#messages"),
  question: document.querySelector("#question"),
  sendButton: document.querySelector("#send-button"),
  uploadSection: document.querySelector("#upload-section"),
  uploadStatus: document.querySelector("#upload-status"),
};

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

function addMessage(role, text, extraClass = "") {
  const message = document.createElement("div");
  message.className = `message ${role} ${extraClass}`;
  message.textContent = text;
  elements.messages.append(message);
  elements.messages.scrollTop = elements.messages.scrollHeight;
  return message;
}

function setChatEnabled(enabled) {
  elements.question.disabled = !enabled;
  elements.sendButton.disabled = !enabled;
}

async function emailSummary() {
  if (state.isWaiting || !state.docId) return;

  state.isWaiting = true;
  setChatEnabled(false);
  elements.emailSummary.disabled = true;
  const originalLabel = elements.emailSummary.textContent;
  elements.emailSummary.textContent = "Sending…";

  try {
    const response = await fetch("/email-summary", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        doc_id: state.docId,
        document_name: elements.documentName.textContent,
      }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(result.detail || "The summary email could not be sent.");
    }
    addMessage("assistant", "The PDF summary was sent to the configured email address.");
  } catch (error) {
    addMessage("assistant", error.message || "The summary email could not be sent.");
  } finally {
    state.isWaiting = false;
    setChatEnabled(true);
    elements.emailSummary.disabled = false;
    elements.emailSummary.textContent = originalLabel;
    elements.question.focus();
  }
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
      body: JSON.stringify({ query, doc_id: state.docId, session_id: state.sessionId }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || !result.answer) {
      throw new Error(result.detail || "The backend could not answer this question.");
    }
    typing.textContent = result.answer;
    typing.classList.remove("typing");
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
elements.emailSummary.addEventListener("click", emailSummary);

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

createSession().catch((error) => setUploadStatus(error.message, "error"));
