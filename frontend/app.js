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

async function uploadPdf(file) {
  if (!file || state.isUploading) return;
  if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
    setUploadStatus("Please select a PDF file.", "error");
    return;
  }

  state.isUploading = true;
  setUploadStatus("Uploading and preparing your document…");
  const data = new FormData();
  data.append("file", file);

  try {
    const response = await fetch("/upload", { method: "POST", body: data });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || !result.doc_id) {
      throw new Error(result.detail || result.error || "The document could not be processed.");
    }

    state.docId = result.doc_id;
    elements.documentName.textContent = file.name;
    elements.uploadSection.hidden = true;
    elements.chatSection.hidden = false;
    elements.messages.replaceChildren();
    addMessage("assistant", "Your PDF is ready. What would you like to know?");
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

elements.fileInput.addEventListener("change", (event) => uploadPdf(event.target.files[0]));
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
elements.dropZone.addEventListener("drop", (event) => uploadPdf(event.dataTransfer.files[0]));

createSession().catch((error) => setUploadStatus(error.message, "error"));
