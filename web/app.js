const state = {
  selectedFile: null,
  selectedExample: null,
  selectedPreviewUrl: null,
  pollTimer: null,
};

const fileInput = document.querySelector("#fileInput");
const dropZone = document.querySelector("#dropZone");
const exampleList = document.querySelector("#exampleList");
const renderButton = document.querySelector("#renderButton");
const doctorButton = document.querySelector("#doctorButton");
const instrumentSelect = document.querySelector("#instrumentSelect");
const pdfPreview = document.querySelector("#pdfPreview");
const previewEmpty = document.querySelector("#previewEmpty");
const statusText = document.querySelector("#statusText");
const audioPlayer = document.querySelector("#audioPlayer");
const logOutput = document.querySelector("#logOutput");

function setStatus(text) {
  statusText.textContent = text;
}

function setLog(text) {
  logOutput.textContent = text || "";
  logOutput.style.display = text ? "block" : "none";
}

function setPreview(url) {
  state.selectedPreviewUrl = url;
  if (!url) {
    pdfPreview.style.display = "none";
    previewEmpty.style.display = "grid";
    pdfPreview.removeAttribute("src");
    return;
  }
  pdfPreview.src = url;
  pdfPreview.style.display = "block";
  previewEmpty.style.display = "none";
}

function updateRenderState() {
  renderButton.disabled = !(state.selectedFile || state.selectedExample);
}

function selectFile(file) {
  state.selectedFile = file;
  state.selectedExample = null;
  document.querySelectorAll(".example-button").forEach((button) => {
    button.classList.remove("is-selected");
  });
  const objectUrl = URL.createObjectURL(file);
  setPreview(objectUrl);
  setStatus(`Ready: ${file.name}`);
  setLog("");
  updateRenderState();
}

function selectExample(pdf, button) {
  state.selectedFile = null;
  state.selectedExample = pdf;
  fileInput.value = "";
  document.querySelectorAll(".example-button").forEach((item) => {
    item.classList.toggle("is-selected", item === button);
  });
  setPreview(pdf.url);
  setStatus(`Ready: ${pdf.name}`);
  setLog("");
  updateRenderState();
}

async function loadExamples() {
  const response = await fetch("/api/pdfs");
  const data = await response.json();
  exampleList.textContent = "";

  if (!data.pdfs.length) {
    const empty = document.createElement("div");
    empty.className = "status-text";
    empty.textContent = "No PDFs found in the PDF folder.";
    exampleList.append(empty);
    return;
  }

  data.pdfs.forEach((pdf) => {
    const button = document.createElement("button");
    button.className = "example-button";
    button.type = "button";
    button.textContent = pdf.name;
    button.addEventListener("click", () => selectExample(pdf, button));
    exampleList.append(button);
  });
}

async function checkTools() {
  setStatus("Checking local tools...");
  const response = await fetch("/api/doctor");
  const data = await response.json();
  setStatus("Tool check complete.");
  setLog(data.report);
}

async function renderPlayback() {
  renderButton.disabled = true;
  audioPlayer.style.display = "none";
  audioPlayer.removeAttribute("src");
  setLog("");
  setStatus("Starting render...");

  const form = new FormData();
  form.set("instrument", instrumentSelect.value);
  if (state.selectedFile) {
    form.set("file", state.selectedFile);
  } else if (state.selectedExample) {
    form.set("existingPdf", state.selectedExample.path);
  }

  const response = await fetch("/api/render", { method: "POST", body: form });
  const data = await response.json();
  if (!response.ok) {
    setStatus(data.error || "Render failed to start.");
    updateRenderState();
    return;
  }

  pollJob(data.jobId);
}

async function pollJob(jobId) {
  window.clearTimeout(state.pollTimer);
  const response = await fetch(`/api/jobs/${jobId}`);
  const job = await response.json();

  if (job.status === "queued" || job.status === "running") {
    setStatus(job.status === "queued" ? "Queued..." : "Rendering playback...");
    state.pollTimer = window.setTimeout(() => pollJob(jobId), 1200);
    return;
  }

  if (job.status === "complete") {
    setStatus(`Ready: ${job.label}`);
    setLog(job.summary || "");
    audioPlayer.src = job.audioUrl;
    audioPlayer.style.display = "block";
    audioPlayer.load();
    updateRenderState();
    return;
  }

  setStatus("Render failed.");
  setLog(job.error || "Unknown error.");
  updateRenderState();
}

fileInput.addEventListener("change", () => {
  if (fileInput.files && fileInput.files[0]) {
    selectFile(fileInput.files[0]);
  }
});

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("is-dragover");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("is-dragover");
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("is-dragover");
  const file = event.dataTransfer.files[0];
  if (file) {
    selectFile(file);
  }
});

doctorButton.addEventListener("click", checkTools);
renderButton.addEventListener("click", renderPlayback);

loadExamples().catch((error) => {
  setStatus("Failed to load PDF folder.");
  setLog(String(error));
});
