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


// ========================================
// EDIT PAGE
// 제작 단계 검토 및 수정
// ========================================

if (document.getElementById("stepList")) {
  const stepList = document.getElementById("stepList");
  const stepCount = document.getElementById("stepCount");
  const addStepBtn = document.getElementById("addStepBtn");
  const confirmEditBtn = document.getElementById("confirmEditBtn");

  const previewVideo = document.getElementById("previewVideo");
  const videoPlaceholder = document.getElementById("videoPlaceholder");

  // 서버에서 전달받은 제작 단계 데이터
  // 현재는 서버가 없으므로 임시 데이터 사용
  let steps = JSON.parse(
    sessionStorage.getItem("analysisSteps") || "null"
  ) || [
    {
      step_id: "step_001",
      order: 1,
      start_sec: 0,
      end_sec: 20.03,
      title: "단계 후보 1",
      transcript_text: "먼저 머리의 눈을 조립합니다.",
      transcript_segment_ids: [0],
      boundary_reason: "video_start",
      needs_review: true,
      target_state_id: null
    },
    {
      step_id: "step_002",
      order: 2,
      start_sec: 20.03,
      end_sec: 36.05,
      title: "단계 후보 2",
      transcript_text: "다음으로 머리와 부리를 조립합니다.",
      transcript_segment_ids: [1],
      boundary_reason: "transition_phrase",
      needs_review: true,
      target_state_id: null
    },
    {
      step_id: "step_003",
      order: 3,
      start_sec: 36.05,
      end_sec: 55.73,
      title: "단계 후보 3",
      transcript_text: "마지막으로 머리와 몸통을 조립합니다.",
      transcript_segment_ids: [2],
      boundary_reason: "transition_phrase",
      needs_review: true,
      target_state_id: null
    }
  ];

  // 영상 미리보기
  const savedUrl = sessionStorage.getItem("uploadedVideoUrl");

  if (savedUrl && previewVideo) {
    previewVideo.src = savedUrl;
    previewVideo.classList.remove("hidden");

    if (videoPlaceholder) {
      videoPlaceholder.classList.add("hidden");
    }
  }

  // 시간 표시용 숫자 변환
  function formatTime(seconds) {
    return Number(seconds).toFixed(2);
  }

  // 단계 목록 화면에 표시
  function renderSteps() {
    stepList.innerHTML = "";

    steps.forEach((step, index) => {
      const item = document.createElement("div");
      item.className = "step-item";
      item.dataset.stepId = step.step_id;

      item.innerHTML = `
        <div class="step-header">
          <strong>STEP ${index + 1}</strong>
          <button type="button" class="delete-step-btn">삭제</button>
        </div>

        <label>단계 제목</label>
        <input
          type="text"
          class="step-title"
          value="${escapeHTML(step.title || "")}"
        >

        <p class="step-transcript">
          ${escapeHTML(step.transcript_text || "음성 분석 내용이 없습니다.")}
        </p>

        <div class="time-inputs">
          <div>
            <label>시작 시간 (초)</label>
            <input
              type="number"
              class="start-time"
              min="0"
              step="0.01"
              value="${formatTime(step.start_sec)}"
            >
          </div>

          <div>
            <label>종료 시간 (초)</label>
            <input
              type="number"
              class="end-time"
              min="0"
              step="0.01"
              value="${formatTime(step.end_sec)}"
            >
          </div>
        </div>
      `;

      stepList.appendChild(item);

      // 제목 수정
      item.querySelector(".step-title").addEventListener("input", (event) => {
        steps[index].title = event.target.value;
      });

      // 시작 시간 수정
      item.querySelector(".start-time").addEventListener("change", (event) => {
        steps[index].start_sec = Number(event.target.value);
      });

      // 종료 시간 수정
      item.querySelector(".end-time").addEventListener("change", (event) => {
        steps[index].end_sec = Number(event.target.value);
      });

      // 단계 삭제
      item.querySelector(".delete-step-btn").addEventListener("click", () => {
        steps.splice(index, 1);
        updateOrder();
        renderSteps();
      });
    });

    stepCount.textContent = steps.length;
  }

  // HTML에 문자열을 삽입할 때 특수문자 처리
  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, (char) => {
      const entities = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      };

      return entities[char];
    });
  }

  // 단계 순서 재정렬
  function updateOrder() {
    steps.forEach((step, index) => {
      step.order = index + 1;
    });
  }

  // 단계 추가
  addStepBtn.addEventListener("click", () => {
    const newStep = {
      step_id: `step_${Date.now()}`,
      order: steps.length + 1,
      start_sec: 0,
      end_sec: 0,
      title: `새로운 단계 ${steps.length + 1}`,
      transcript_text: "",
      transcript_segment_ids: [],
      boundary_reason: "manual",
      needs_review: true,
      target_state_id: null
    };

    steps.push(newStep);

    updateOrder();
    renderSteps();
  });

  // 편집 확인
  confirmEditBtn.addEventListener("click", () => {
    // 모든 입력값을 최신 상태로 반영
    const items = stepList.querySelectorAll(".step-item");

    items.forEach((item, index) => {
      steps[index].title =
        item.querySelector(".step-title").value;

      steps[index].start_sec =
        Number(item.querySelector(".start-time").value);

      steps[index].end_sec =
        Number(item.querySelector(".end-time").value);
    });

    // 시간 유효성 검사
    for (const step of steps) {
      if (
        !Number.isFinite(step.start_sec) ||
        !Number.isFinite(step.end_sec) ||
        step.start_sec < 0 ||
        step.end_sec <= step.start_sec
      ) {
        alert("각 단계의 시작 시간과 종료 시간을 확인해주세요.");
        return;
      }
    }

    updateOrder();

    // 수정된 데이터 저장
    sessionStorage.setItem(
      "editedSteps",
      JSON.stringify(steps)
    );

    // 서버 연동 시 이 위치에서 수정된 JSON 전송
    console.log("수정 완료된 제작 단계:", steps);

    alert("제작 단계 수정이 완료되었습니다.");

    window.location.href = "./connect.html";
  });

  // 최초 화면 표시
  renderSteps();
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

  // GitHub Pages에 배포된 모바일 페이지 주소
  const mobileUrl =
    `https://muoleo.github.io/FollowAlong/frontend/mobile.html?session=${encodeURIComponent(sessionId)}`;

  console.log("QR 코드 연결 주소:", mobileUrl);

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

// ------------------------------------------------------------
// mobile.html : 카메라 실행 및 전환
// ------------------------------------------------------------

const params = new URLSearchParams(window.location.search);
const sessionId = params.get("session") || "DEMO";

// HTML 요소
const video = document.getElementById("camera");
const overlay = document.getElementById("cameraOverlay");
const startBtn = document.getElementById("startCameraBtn");
const switchBtn = document.getElementById("switchCameraBtn");
const recordBtn = document.getElementById("recordBtn");
const stopBtn = document.getElementById("stopBtn");
const status = document.getElementById("mobileStatus");
const sessionMessage = document.getElementById("sessionMessage");

// 카메라 및 녹화 상태
let currentFacingMode = "environment";
let currentStream = null;
let recorder = null;
let chunks = [];

// Frame Capture 상태
const canvas = document.createElement("canvas");
const context = canvas.getContext("2d");
let captureTimer = null;

// 세션 표시
if (sessionMessage) {
  sessionMessage.textContent =
    `세션 ${sessionId}에 연결되었습니다.`;
}

// 카메라 실행
async function startCamera() {
  try {
    if (currentStream) {
      currentStream.getTracks().forEach(track => track.stop());
      currentStream = null;
    }

    currentStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: currentFacingMode },
        width: { ideal: 1280 },
        height: { ideal: 720 }
      },
      audio: true
    });

    video.srcObject = currentStream;
    await video.play();

     // 안내 화면 숨기기
    overlay?.classList.add("hidden");

    startBtn?.classList.add("hidden");
    recordBtn?.classList.remove("hidden");

    if (status) {
      status.textContent = "카메라가 연결되었습니다.";
    }

  } catch (error) {
    console.error("카메라 실행 실패:", error);

     // 실패하면 안내 화면 다시 표시
    overlay?.classList.remove("hidden");

    if (status) {
      status.textContent = "카메라를 실행할 수 없습니다.";
    }
  }
}

// 카메라 시작 버튼
startBtn?.addEventListener("click", startCamera);

// 전면 / 후면 카메라 전환
switchBtn?.addEventListener("click", async () => {
  if (recorder && recorder.state === "recording") {
    alert("촬영 중에는 카메라를 전환할 수 없습니다.");
    return;
  }

  currentFacingMode =
    currentFacingMode === "environment"
      ? "user"
      : "environment";

  await startCamera();
});

// Frame Capture
function captureFrame() {
  if (!currentStream || video.readyState < 2) return;

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;

  context.drawImage(
    video,
    0,
    0,
    canvas.width,
    canvas.height
  );

  canvas.toBlob(async blob => {
    if (!blob) return;

    await sendFrameToServer(blob);
  }, "image/jpeg", 0.8);
}

// 프레임 서버 전송
async function sendFrameToServer(blob) {
  const formData = new FormData();

  formData.append("frame", blob, "frame.jpg");
  formData.append("sessionId", sessionId);
  formData.append("capturedAt", new Date().toISOString());

  try {
    const response = await fetch(
      "https://YOUR_SERVER_ADDRESS/api/frames",
      {
        method: "POST",
        body: formData
      }
    );

    if (!response.ok) {
      throw new Error("이미지 전송 실패: " + response.status);
    }

    console.log("프레임 전송 성공");

  } catch (error) {
    console.error("서버 전송 오류:", error);
  }
}

// 3초마다 프레임 캡처
function startFrameCapture() {
  if (captureTimer) return;

  captureFrame();

  captureTimer = setInterval(() => {
    captureFrame();
  }, 3000);
}

// 프레임 캡처 종료
function stopFrameCapture() {
  if (captureTimer) {
    clearInterval(captureTimer);
    captureTimer = null;
  }
}

// 촬영 시작
recordBtn?.addEventListener("click", () => {
  if (!currentStream) return;

  chunks = [];

  recorder = new MediaRecorder(currentStream);

  recorder.ondataavailable = event => {
    if (event.data.size > 0) {
      chunks.push(event.data);
    }
  };

  recorder.onstop = () => {
    const blob = new Blob(chunks, {
      type: recorder.mimeType || "video/webm"
    });

    const sizeMB = (blob.size / 1024 / 1024).toFixed(2);

    console.log("녹화 영상:", blob);

    if (status) {
      status.textContent =
        `촬영 완료 · ${sizeMB} MB`;
    }

    recordBtn?.classList.remove("hidden");
    stopBtn?.classList.add("hidden");
  };

  recorder.start();

  // 녹화 시작과 동시에 프레임 캡처 시작
  startFrameCapture();

  recordBtn.classList.add("hidden");
  stopBtn?.classList.remove("hidden");

  if (status) {
    status.textContent = "촬영 중입니다...";
  }
});

// 촬영 종료
stopBtn?.addEventListener("click", () => {
  stopFrameCapture();

  if (recorder && recorder.state !== "inactive") {
    recorder.stop();
  }
});


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
