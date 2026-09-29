// ============================================================
// VideoFlow Demo
// 서버가 아직 없을 때 사용하는 프론트엔드 데모 로직
// ============================================================

const $ = (selector) => document.querySelector(selector);

// ------------------------------------------------------------
// index.html : 영상 선택 / 업로드
// ------------------------------------------------------------
const videoInput = $("#videoInput");
const dropZone = $("#dropZone");
const uploadBtn = $("#uploadBtn");
const fileInfo = $("#fileInfo");
const message = $("#message");
const loadingModal = $("#loadingModal");

let selectedFile = null;

if (videoInput) {
  videoInput.addEventListener("change", () => {
    handleFile(videoInput.files[0]);
  });
}

if (dropZone) {
  ["dragenter", "dragover"].forEach(eventName => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.add("dragging");
    });
  });

  ["dragleave", "drop"].forEach(eventName => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.remove("dragging");
    });
  });

  dropZone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    handleFile(file);
  });
}

function handleFile(file) {
  if (!file) return;

  if (!file.type.startsWith("video/")) {
    selectedFile = null;
    uploadBtn.disabled = true;
    fileInfo.classList.add("hidden");
    message.textContent = "동영상 파일만 업로드할 수 있습니다.";
    message.className = "message error";
    return;
  }

  selectedFile = file;
  uploadBtn.disabled = false;

  const sizeMB = (file.size / 1024 / 1024).toFixed(2);

  fileInfo.innerHTML = `
    <span class="file-icon">🎞️</span>
    <div>
      <strong>${escapeHtml(file.name)}</strong>
      <small>${sizeMB} MB · ${file.type}</small>
    </div>
  `;

  fileInfo.classList.remove("hidden");
  message.textContent = "업로드할 영상을 확인했습니다.";
  message.className = "message success";
}

if (uploadBtn) {
  uploadBtn.addEventListener("click", () => {
    if (!selectedFile) return;

    // 브라우저 세션에 파일 URL을 저장해 편집 페이지에서 미리보기
    const objectUrl = URL.createObjectURL(selectedFile);
    sessionStorage.setItem("uploadedVideoUrl", objectUrl);
    sessionStorage.setItem("uploadedVideoName", selectedFile.name);

    showProcessingModal();
  });
}

function showProcessingModal() {
  loadingModal.classList.remove("hidden");

  let progress = 0;
  const progressBar = $("#progressBar");
  const progressText = $("#progressText");

  const timer = setInterval(() => {
    progress += Math.floor(Math.random() * 15) + 5;
    if (progress >= 100) {
      progress = 100;
      clearInterval(timer);

      setTimeout(() => {
        window.location.href = "edit.html";
      }, 500);
    }

    progressBar.style.width = `${progress}%`;
    progressText.textContent = `${progress}%`;
  }, 300);
}

// ------------------------------------------------------------
// connect.html : 세션 ID + QR 코드 생성
// ------------------------------------------------------------
const qrCode = $("#qrCode");
const sessionIdElement = $("#sessionId");

if (qrCode && sessionIdElement) {
  const sessionId =
    "VF-" +
    Math.random().toString(36).substring(2, 8).toUpperCase();

  sessionStorage.setItem("sessionId", sessionId);
  sessionIdElement.textContent = sessionId;

  // 현재 페이지의 경로를 기준으로 mobile.html 주소 생성
  const mobileUrl =
    `${window.location.origin}${window.location.pathname.replace(/connect\.html$/, "")}` +
    `mobile.html?session=${encodeURIComponent(sessionId)}`;

  if (typeof QRCode !== "undefined") {
    qrCode.innerHTML = "";

    new QRCode(qrCode, {
      text: mobileUrl,
      width: 220,
      height: 220,
      correctLevel: QRCode.CorrectLevel.M
    });
  } else {
    qrCode.innerHTML = `
      <div class="qr-fallback">
        QR 라이브러리를 불러오지 못했습니다.<br><br>
        <small>${escapeHtml(mobileUrl)}</small>
      </div>
    `;
  }
}

const backBtn = $("#backBtn");

if (backBtn) {
  backBtn.addEventListener("click", () => {
    sessionStorage.clear();
    window.location.href = "index.html";
  });
}

// ------------------------------------------------------------
// Utility
// ------------------------------------------------------------
function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
