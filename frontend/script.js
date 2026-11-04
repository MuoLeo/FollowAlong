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
// 제작 단계 검토 및 타임라인 경계선 편집
// 기존 script.js의 EDIT PAGE 블록을 이 코드로 교체하세요.
// 업로드 / Connect / Mobile 코드는 그대로 유지합니다.
// ========================================

if (document.getElementById("stepList")) {
  const stepList = document.getElementById("stepList");
  const stepCount = document.getElementById("stepCount");
  const confirmEditBtn = document.getElementById("confirmEditBtn");
  const previewVideo = document.getElementById("previewVideo");
  const videoPlaceholder = document.getElementById("videoPlaceholder");

  const timelineTrack = document.getElementById("timelineTrack");
  const timelineDuration = document.getElementById("timelineDuration");
  const boundaryHint = document.getElementById("boundaryHint");
  const deleteBoundaryBtn = document.getElementById("deleteBoundaryBtn");

  const MIN_STEP_SECONDS = 1;
  const EPSILON = 0.0001;

  let steps = JSON.parse(sessionStorage.getItem("editedSteps") || 
  sessionStorage.getItem("analysisSteps") || "null") || [
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

  let duration = Math.max(
    0,
    ...steps.map(step => Number(step.end_sec) || 0)
  );
  let selectedBoundaryIndex = null; // i는 steps[i]와 steps[i + 1] 사이 경계
  let draggingBoundaryIndex = null;

  // 영상 미리보기
  const savedUrl = sessionStorage.getItem("uploadedVideoUrl");
  if (savedUrl && previewVideo) {
    previewVideo.src = savedUrl;
    previewVideo.classList.remove("hidden");
    if (videoPlaceholder) videoPlaceholder.classList.add("hidden");

    previewVideo.addEventListener("loadedmetadata", () => {
      if (Number.isFinite(previewVideo.duration) && previewVideo.duration > 0) {
        duration = previewVideo.duration;
        normalizeSteps();
        renderAll();
      }
    });
  }

  function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    })[char]);
  }

  function formatTime(seconds) {
    const safe = Math.max(0, Number(seconds) || 0);
    const minutes = Math.floor(safe / 60);
    const remaining = (safe % 60).toFixed(2).padStart(5, "0");
    return `${String(minutes).padStart(2, "0")}:${remaining}`;
  }

  function updateOrder() {
    steps.forEach((step, index) => {
      step.order = index + 1;
    });
  }

  // 모든 구간이 0초부터 영상 끝까지 연속되도록 정리
  function normalizeSteps() {
    if (!steps.length) return;

    if (!Number.isFinite(duration) || duration <= 0) {
      duration = Math.max(...steps.map(step => Number(step.end_sec) || 0), 1);
    }

    // 영상 길이가 단계 수보다 짧은 특수 상황에서는 뒤쪽 단계를 합쳐
    // 모든 단계가 최소 1초를 확보할 수 있도록 한다.
    while (steps.length > 1 && duration + EPSILON < steps.length * MIN_STEP_SECONDS) {
      const last = steps.pop();
      const previous = steps[steps.length - 1];
      previous.end_sec = last.end_sec;
      previous.transcript_text = [previous.transcript_text, last.transcript_text]
        .filter(Boolean).join(" ");
    }

    let cursor = 0;
    for (let i = 0; i < steps.length; i++) {
      const remainingSegments = steps.length - i - 1;
      const oldEnd = Number(steps[i].end_sec);
      const minEnd = cursor + MIN_STEP_SECONDS;
      const maxEnd = duration - remainingSegments * MIN_STEP_SECONDS;

      steps[i].start_sec = cursor;

      if (i === steps.length - 1) {
        steps[i].end_sec = duration;
      } else {
        const proposed = Number.isFinite(oldEnd) ? oldEnd : minEnd;
        steps[i].end_sec = Math.min(maxEnd, Math.max(minEnd, proposed));
      }
      cursor = steps[i].end_sec;
    }

    updateOrder();
    if (
      selectedBoundaryIndex !== null &&
      (selectedBoundaryIndex < 0 || selectedBoundaryIndex >= steps.length - 1)
    ) {
      selectedBoundaryIndex = null;
    }
  }

  function renderStepList() {
    stepList.innerHTML = "";

    steps.forEach((step, index) => {
      const item = document.createElement("article");
      item.className = "step-item";
      item.innerHTML = `
        <div class="step-header">
          <strong>STEP ${index + 1}</strong>
          <span class="step-duration">${formatTime(step.end_sec - step.start_sec)}</span>
        </div>

        <label for="step-title-${index}">단계 제목</label>
        <input
          id="step-title-${index}"
          type="text"
          class="step-title"
          value="${escapeHTML(step.title || "")}"
          placeholder="단계 제목"
        >
        
        <div class="step-transcript">
          <label>Transcript</label>
          <textarea
              class="transcript-input"
              placeholder="음성 인식 내용을 입력하세요."
          ></textarea>
        </div>

        <div class="time-inputs">
          <div>
            <label>시작 시간</label>
            <input type="text" class="start-time" value="${formatTime(step.start_sec)}" readonly>
          </div>
          <div>
            <label>종료 시간</label>
            <input type="text" class="end-time" value="${formatTime(step.end_sec)}" readonly>
          </div>
        </div>
      `;
      
      const transcriptInput = item.querySelector(".transcript-input");
      transcriptInput.value = step.transcript_text || "";
      transcriptInput.addEventListener("input", (e) => {
          step.transcript_text = e.target.value;
      });

      item.querySelector(".step-title").addEventListener("input", event => {
        steps[index].title = event.target.value;
        renderTimelineLabels();
      });

      stepList.appendChild(item);
    });

    stepCount.textContent = `총 ${steps.length}단계`;
  }

  function renderTimelineLabels() {
    timelineTrack.querySelectorAll(".timeline-segment-label").forEach((label, index) => {
      label.textContent = `STEP ${index + 1}`;
      label.title = steps[index]?.title || `STEP ${index + 1}`;
    });
  }

  function renderTimeline() {
    timelineTrack.innerHTML = "";

    steps.forEach((step, index) => {
      const segment = document.createElement("div");
      segment.className = "timeline-segment";
      segment.style.left = `${(step.start_sec / duration) * 100}%`;
      segment.style.width = `${((step.end_sec - step.start_sec) / duration) * 100}%`;
      segment.innerHTML = `
        <span class="timeline-segment-label" title="${escapeHTML(step.title || "")}">
          STEP ${index + 1}
        </span>
        <span class="timeline-segment-time">
          ${formatTime(step.start_sec)}–${formatTime(step.end_sec)}
        </span>
      `;
      timelineTrack.appendChild(segment);
    });

    // 각 단계 사이에 하나씩 경계선을 표시
    for (let i = 0; i < steps.length - 1; i++) {
      const boundary = document.createElement("button");
      boundary.type = "button";
      boundary.className = "timeline-boundary";
      boundary.dataset.boundaryIndex = i;
      boundary.style.left = `${(steps[i].end_sec / duration) * 100}%`;
      boundary.setAttribute("aria-label", `STEP ${i + 1}과 STEP ${i + 2} 사이 경계선`);

      if (selectedBoundaryIndex === i) boundary.classList.add("selected");

      boundary.addEventListener("pointerdown", event => {
        event.preventDefault();
        event.stopPropagation();
        selectedBoundaryIndex = i;
        draggingBoundaryIndex = i;
        boundary.classList.add("selected");
        deleteBoundaryBtn.disabled = false;
        boundaryHint.textContent = `STEP ${i + 1}과 STEP ${i + 2} 사이 경계선 선택됨`;
        boundary.setPointerCapture(event.pointerId);
      });

      boundary.addEventListener("pointermove", event => {
        if (draggingBoundaryIndex !== i) return;
        const rect = timelineTrack.getBoundingClientRect();
        const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
        const requestedTime = ratio * duration;
        moveBoundary(i, requestedTime, false);
      });

      const finishDrag = () => {
        if (draggingBoundaryIndex !== i) return;
        draggingBoundaryIndex = null;
        renderAll();
      };
      boundary.addEventListener("pointerup", finishDrag);
      boundary.addEventListener("pointercancel", finishDrag);

      boundary.addEventListener("click", event => {
        event.stopPropagation();
        selectedBoundaryIndex = i;
        updateBoundarySelection();
      });

      timelineTrack.appendChild(boundary);
    }

    timelineDuration.textContent = `전체 ${formatTime(duration)}`;
    updateBoundarySelection();
  }

  function updateBoundarySelection() {
    timelineTrack.querySelectorAll(".timeline-boundary").forEach((element, index) => {
      element.classList.toggle("selected", index === selectedBoundaryIndex);
    });

    const hasSelection = selectedBoundaryIndex !== null;
    deleteBoundaryBtn.disabled = !hasSelection;

    if (hasSelection) {
      boundaryHint.textContent =
        `STEP ${selectedBoundaryIndex + 1}과 STEP ${selectedBoundaryIndex + 2} 사이 경계선 선택됨`;
    } else {
      boundaryHint.textContent = "경계선을 선택하면 위치를 이동하거나 삭제할 수 있습니다.";
    }
  }

  function updateTimelineGeometry() {
    const segments = timelineTrack.querySelectorAll(".timeline-segment");
    segments.forEach((segment, index) => {
      const step = steps[index];
      segment.style.left = `${(step.start_sec / duration) * 100}%`;
      segment.style.width = `${((step.end_sec - step.start_sec) / duration) * 100}%`;
      const time = segment.querySelector(".timeline-segment-time");
      if (time) time.textContent = `${formatTime(step.start_sec)}–${formatTime(step.end_sec)}`;
    });

    const boundaries = timelineTrack.querySelectorAll(".timeline-boundary");
    boundaries.forEach((boundary, index) => {
      boundary.style.left = `${(steps[index].end_sec / duration) * 100}%`;
    });
  }

  // 경계선을 이동하되 양옆 단계가 각각 최소 1초를 유지하게 한다.
  function moveBoundary(index, requestedTime, rerender) {
    if (index < 0 || index >= steps.length - 1) return;

    const minTime = steps[index].start_sec + MIN_STEP_SECONDS;
    const maxTime = steps[index + 1].end_sec - MIN_STEP_SECONDS;
    const nextTime = Math.min(maxTime, Math.max(minTime, requestedTime));

    steps[index].end_sec = nextTime;
    steps[index + 1].start_sec = nextTime;

    if (rerender) renderAll();
    else updateTimelineGeometry();
  }

  // 타임라인 더블클릭: 클릭한 구간 하나만 둘로 분할
  timelineTrack.addEventListener("dblclick", event => {
    if (event.target.closest(".timeline-boundary")) return;

    const rect = timelineTrack.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    const clickedTime = ratio * duration;

    const stepIndex = steps.findIndex(step =>
      clickedTime > step.start_sec + EPSILON &&
      clickedTime < step.end_sec - EPSILON
    );

    if (stepIndex === -1) return;

    const original = steps[stepIndex];
    const splitTime = Math.min(
      original.end_sec - MIN_STEP_SECONDS,
      Math.max(original.start_sec + MIN_STEP_SECONDS, clickedTime)
    );

    if (
      splitTime - original.start_sec < MIN_STEP_SECONDS - EPSILON ||
      original.end_sec - splitTime < MIN_STEP_SECONDS - EPSILON
    ) {
      alert("각 단계는 최소 1초 이상이어야 합니다.");
      return;
    }

    const nextStep = {
      ...original,
      step_id: `step_${Date.now()}_${Math.floor(Math.random() * 10000)}`,
      start_sec: splitTime,
      end_sec: original.end_sec,
      title: `${original.title || `단계 ${stepIndex + 1}`} (분할)`,
      transcript_segment_ids: Array.isArray(original.transcript_segment_ids)
        ? [...original.transcript_segment_ids]
        : [],
      boundary_reason: "manual",
      needs_review: true
    };

    original.end_sec = splitTime;
    steps.splice(stepIndex + 1, 0, nextStep);
    selectedBoundaryIndex = stepIndex;
    updateOrder();
    renderAll();
  });

  // 선택한 경계선 삭제 = 양옆 두 단계를 하나로 병합
  deleteBoundaryBtn.addEventListener("click", () => {
    const index = selectedBoundaryIndex;
    if (index === null || index < 0 || index >= steps.length - 1) return;

    const previous = steps[index];
    const next = steps[index + 1];

    previous.end_sec = next.end_sec;

    const previousText = previous.transcript_text || "";
    const nextText = next.transcript_text || "";
    if (nextText && nextText !== previousText) {
      previous.transcript_text = [previousText, nextText].filter(Boolean).join(" ");
    }

    const previousIds = Array.isArray(previous.transcript_segment_ids)
      ? previous.transcript_segment_ids
      : [];
    const nextIds = Array.isArray(next.transcript_segment_ids)
      ? next.transcript_segment_ids
      : [];
    previous.transcript_segment_ids = [...new Set([...previousIds, ...nextIds])];

    previous.boundary_reason = "manual_merge";
    previous.needs_review = true;

    steps.splice(index + 1, 1);
    selectedBoundaryIndex = null;
    updateOrder();
    renderAll();
  });

  // Delete 키로도 선택 경계선을 삭제할 수 있음
  document.addEventListener("keydown", event => {
    const target = event.target;
    const editingText = target && (
      target.tagName === "INPUT" ||
      target.tagName === "TEXTAREA" ||
      target.isContentEditable
    );
    if (event.key === "Delete" && !editingText && selectedBoundaryIndex !== null) {
      deleteBoundaryBtn.click();
    }
  });

  function renderAll() {
    normalizeSteps();
    renderStepList();
    renderTimeline();
  }

  // 편집 확인: 연속 구간 / 최소 길이 검사 후 저장
  confirmEditBtn.addEventListener("click", () => {
    normalizeSteps();

    if (!steps.length) {
      alert("최소 한 개 이상의 제작 단계가 필요합니다.");
      return;
    }

    let expectedStart = 0;
    for (const step of steps) {
      if (
        !Number.isFinite(step.start_sec) ||
        !Number.isFinite(step.end_sec) ||
        Math.abs(step.start_sec - expectedStart) > 0.01 ||
        step.end_sec - step.start_sec < MIN_STEP_SECONDS - EPSILON
      ) {
        alert("타임라인을 확인해주세요. 단계 사이에 공백이나 겹침이 없어야 하며, 각 단계는 최소 1초 이상이어야 합니다.");
        return;
      }
      expectedStart = step.end_sec;
    }

    if (Math.abs(expectedStart - duration) > 0.01) {
      alert("마지막 단계의 종료 시간이 영상 길이와 일치하지 않습니다.");
      return;
    }

    updateOrder();
    sessionStorage.setItem("editedSteps", JSON.stringify(steps));
    console.log("수정 완료된 제작 단계:", steps);
    alert("제작 단계 수정이 완료되었습니다.");
    window.location.href = "./connect.html";
  });

  // 최초 화면 표시
  normalizeSteps();
  renderAll();
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

// 0.5초마다 프레임 캡처
function startFrameCapture() {
  if (captureTimer) return;

  captureFrame();

  captureTimer = setInterval(() => {
    captureFrame();
  }, 500);
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
