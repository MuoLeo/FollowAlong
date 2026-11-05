// FollowAlong 제작 가이드 - 서버 없이 판정 결과를 버튼으로 시뮬레이션
(() => {
  const video = document.getElementById("guideVideo");
  if (!video) return;

  const titleEl = document.getElementById("guideStepTitle");
  const numberEl = document.getElementById("guideStepNumber");
  const transcriptEl = document.getElementById("guideTranscript");
  const statusEl = document.getElementById("guideStatus");
  const listEl = document.getElementById("guideStepList");
  const progressBar = document.getElementById("guideProgressBar");
  const timeLabel = document.getElementById("guideTimeLabel");
  const placeholder = document.getElementById("guideVideoPlaceholder");
  const currentStepBtn = document.getElementById("currentStepBtn");
  const nextStepBtn = document.getElementById("nextStepBtn");
  const backBtn = document.getElementById("backToConnectBtn");

  let steps = [];
  try { steps = JSON.parse(sessionStorage.getItem("editedSteps") || "[]"); }
  catch (error) { console.error("제작 단계 데이터를 읽지 못했습니다.", error); }

  const videoUrl = sessionStorage.getItem("uploadedVideoUrl");
  let currentIndex = 0;
  const completed = new Set();

  function setStatus(message, type = "neutral") {
    statusEl.textContent = message;
    statusEl.className = `guide-status ${type}`;
  }

  function renderList() {
    listEl.innerHTML = "";
    steps.forEach((step, index) => {
      const item = document.createElement("li");
      item.textContent = `${index + 1}. ${step.title || `단계 ${index + 1}`}`;
      if (index === currentIndex) item.classList.add("active");
      if (completed.has(index)) item.classList.add("completed");
      item.addEventListener("click", () => {
        currentIndex = index;
        showStep(true);
        setStatus(`${index + 1}단계 안내 영상을 재생합니다.`, "neutral");
      });
      listEl.appendChild(item);
    });
  }

  function updateProgress() {
    if (!steps.length) return;
    const step = steps[currentIndex];
    const start = Number(step.start_sec);
    const end = Number(step.end_sec);
    const duration = Math.max(0.01, end - start);
    const elapsed = Math.min(Math.max(video.currentTime - start, 0), duration);
    progressBar.style.width = `${elapsed / duration * 100}%`;
    timeLabel.textContent = `${elapsed.toFixed(2)}초 / ${duration.toFixed(2)}초`;
  }

  function showStep(play) {
    if (!steps.length) return;
    const step = steps[currentIndex];
    const start = Number(step.start_sec);
    titleEl.textContent = step.title || `단계 ${currentIndex + 1}`;
    numberEl.textContent = `STEP ${currentIndex + 1} / ${steps.length}`;
    transcriptEl.textContent = step.transcript_text || "이 단계에 대한 음성 안내가 없습니다.";
    renderList();

    if (!videoUrl) {
      placeholder.classList.remove("hidden");
      setStatus("원본 영상 주소가 없습니다. 처음 화면에서 영상을 다시 업로드해주세요.", "warning");
      return;
    }

    placeholder.classList.add("hidden");
    if (video.src !== videoUrl) video.src = videoUrl;
    video.pause();
    video.currentTime = Math.max(0, start);
    if (play) {
      const promise = video.play();
      if (promise) promise.catch(() => setStatus("영상의 재생 버튼을 눌러 재생해주세요.", "warning"));
    }
    updateProgress();
  }

  video.addEventListener("loadedmetadata", () => {
    if (steps.length) {
      video.currentTime = Math.max(0, Number(steps[currentIndex].start_sec) || 0);
      updateProgress();
    }
  });

  video.addEventListener("timeupdate", () => {
    if (!steps.length) return;
    const end = Number(steps[currentIndex].end_sec);
    updateProgress();
    if (video.currentTime >= end) {
      video.pause();
      video.currentTime = end;
      updateProgress();
      setStatus("현재 단계 영상이 끝났습니다. 조립 후 판정 결과를 선택해주세요.", "neutral");
    }
  });

  function replayCurrentStep() {
    if (!steps.length) return;

    const start = Number(steps[currentIndex].start_sec);

    video.pause();
    video.currentTime = start;

    const promise = video.play();
    if (promise) {
        promise.catch(() => {
            setStatus("영상의 재생 버튼을 눌러 재생해주세요.", "warning");
        });
    }

    setStatus("현재 단계를 다시 재생합니다.", "neutral");
  }

  function goToNextStep() {
    if (!steps.length) return;

    if (currentIndex >= steps.length - 1) {
        video.pause();
        setStatus("모든 제작 단계를 완료했습니다! 🎉", "success");
        return;
    }

    currentIndex += 1;
    showStep(true);

    setStatus(
        `${currentIndex + 1}단계 안내 영상을 재생합니다.`,
        "neutral"
    );
  }

  currentStepBtn.addEventListener("click", replayCurrentStep);
  nextStepBtn.addEventListener("click", goToNextStep);

  backBtn.addEventListener("click", () => { window.location.href = "./connect.html"; });
  
  function handleAIResult(result) {
    switch (result) {
        case "obscured":
            video.pause();
            setStatus(
                "완성한 레고를 화면에 비춰주세요.",
                "warning"
            );
            break;

        case "incorrect":
            replayCurrentStep();
            setStatus(
                "잘못 조립했어요. 현재 단계를 다시 확인해주세요.",
                "error"
            );
            break;

        case "correct":
            goToNextStep();
            setStatus(
                "올바르게 조립했습니다! 다음 단계로 이동합니다.",
                "success"
            );
            break;
    }
  }
  if (!steps.length) {
    titleEl.textContent = "제작 단계가 없습니다.";
    numberEl.textContent = "STEP - / -";
    transcriptEl.textContent = "edit.html에서 단계를 저장한 뒤 다시 진행해주세요.";
    setStatus("저장된 제작 단계 데이터가 없습니다.", "warning");
    doneBtn.disabled = obscuredBtn.disabled = wrongBtn.disabled = true;
    return;
  }

  if (videoUrl) {
    video.src = videoUrl;
    placeholder.classList.add("hidden");
  }
  showStep(false);
  setStatus("데모 준비 완료. 조립 상태 판정 버튼으로 동작을 확인할 수 있습니다.", "neutral");
})();
