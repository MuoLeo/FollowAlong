# FollowAlong V5.0 로컬 연결 확인

목적: Kaggle에서 평가한 모델을 실제 HTTP 서버에 연결하고, 기존 영상으로 정상 조립 흐름이 동작하는지 확인합니다. 추가 학습은 없습니다. 기존 V4.6 폴더는 수정하지 않고 이 새 폴더에서 진행하세요.

## 1. 압축 풀고 VS Code에서 폴더 열기

ZIP을 전부 압축 해제합니다. VS Code의 파일 → 폴더 열기로 **01_setup.ps1, 02_start_server.ps1, model_bundle이 보이는 폴더**를 여세요. 겉 폴더만 열었다면 내부 FollowAlong_V50_local 폴더를 한 번 더 여세요.

기존 VS Code 창과 서버는 닫아도 됩니다. 예전 파일을 삭제할 필요는 없습니다. 이번 서버는 별도 포트8767을 사용합니다. Kaggle에서 추가로 실행할 것은 없습니다.

## 2. 최초 설치 — 터미널1

VS Code 터미널 → 새 터미널에서 다음 명령을 실행합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\01_setup.ps1
```

이 폴더 전용 .venv를 만들고 라이브러리를 설치합니다. Python3.11이 필요하며 사용자 PC에서 이미 쓰던 버전입니다. 설치 중에는 다운로드가 오래 걸릴 수 있습니다. 끝에 SETUP OK가 나오면 다음 단계로 갑니다. 활성화 명령을 따로 입력할 필요는 없습니다.

## 3. 실제 모델 서버 시작 — 같은 터미널1

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\02_start_server.ps1
```

다음과 같은 로그가 나와야 합니다.

```text
Listening http://127.0.0.1:8767 | model_mode=real_v50 | N=3 | Stage5 rider gate | NO GENERAL ERROR VERIFIER
```

이 터미널은 계속 켜둡니다. Transformer의 norm_first 경고만 나오고 이어서 Listening이 뜨면 경고 때문에 중단된 것이 아닙니다.

## 4. 실제 영상 전송 — 새 터미널2

터미널 → 새 터미널을 열고 아래 명령을 실행하세요.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\03_replay_video.ps1
```

파일 선택 창에서 추가 촬영 영상 **fullstage_val_02.mp4**를 선택합니다. 영상이 ZIP 안에 있다면 Windows 탐색기로 먼저 압축을 풀어 실제 mp4를 선택하세요.

0.5초마다의 영상을 무손실 PNG로 보내고 실제 모델 응답을 받습니다. CPU이므로 영상 길이보다 오래 걸릴 수 있습니다. 실시간 카메라 속도 검증은 아직 아닙니다.

이 스크립트는 정상 조립 영상의 통신 흐름을 확인하기 위해 외부 검사의 정상 응답과 서버의 다음 단계 승인을 **클라이언트에서 흉내 냅니다**. 조원 서버나 오류 판정 모델이 연결된 것이 아닙니다. AI 서버 자체의 auto_advance는 계속 false입니다. 승인 흉내 없이 첫 후보에서 멈추려면 다음 명령을 직접 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m followalong_v50.replay
```

## 5. 결과 ZIP 보내기

끝에 RESULT ZIP: ...\results\v50_api_날짜_식별자.zip이 표시됩니다. 그 ZIP을 보내주세요. 후보가 다섯 개 나오지 않거나 오류가 나도 임계값을 바꾸지 말고 결과 ZIP과 콘솔 내용을 보내면 됩니다.

Kaggle 참고 시각은 Stage1 25.5 / Stage2 50.0 / Stage3 78.5 / Stage4 108.5 / Stage5 168.5초입니다. Windows·라이브러리·장치가 다르므로 실제 추론으로 같은지 확인해야 합니다. 이 재생은 이미 평가한 영상을 사용하는 통합 점검으로, 새 독립 성능평가가 아닙니다.

## 현재 적용 정책

- V4.7 candidate_new604 temporal 모델과 기존 SupCon ResNet50 encoder·prototype 사용.
- 최근5프레임,0.5초 간격,완료 점수0.5 이상3회 연속.
- Stage5는 같은 양성 판정마다 rider 점수도0.5 이상. ROI [.45,.48,.9,.96]은 고정 카메라 배치 전용.
- 경량화를 위해 Stage5 temporal 점수가0.5 미만일 때 ROI encoder 실행을 생략합니다. 이 경우 연속 확인은 어차피0으로 돌아가므로 선택된 정책의 판단 조건은 같습니다.
- 일반 단계 변경 때 최근 프레임은 유지하고 연속 확인 횟수는0으로 초기화합니다. 이는 최종 Kaggle 평가와 같습니다. 재확인(retry) 때는 버퍼와 연속 횟수를 비우며 새 프레임7장이 있어야 후보가 가능합니다.
- 완료 후보가 나오면 외부 검사 대기. 오류/가림 판정은 외부 또는 수동으로만 제공하며 별도 AI 모델은 없습니다. 탑승 검증 점수가 낮아도 오조립으로 단정하지 않습니다.
- invalid 처리 후 재생 요청은 한 번만 발생하고, 계속 들어오는 프레임으로 재생을 반복 요청하지 않습니다. 재확인은 retry가 명시적으로 들어와야 시작됩니다.
- 현재 포트는 로컬127.0.0.1 전용입니다. 스마트폰·조원 서버 원격 연결과 인증은 다음 단계입니다.

## 검증 범위

개발 환경에서42개 프로토콜·워크플로 테스트를 통과했고, 저장된 영상02 점수를 서버 상태 관리에 입력해 완료 시각5개가 기존 결과와 일치함을 확인했습니다. 개발 환경에는 torch/OpenCV가 없어 실제 checkpoint를 이용한 Windows 영상 추론은 실행하지 못했습니다. 이번 사용자 실행이 그 확인 단계입니다. 모델4개 파일은 원래 결과와 SHA256이 같은지 검증했습니다.

## 이후 진행

이번 결과를 확인한 뒤 조원 서버의 프레임·초기 단계·단계 변경 이벤트를 연결합니다. 그다음 스마트폰 실촬영 지연과 재시도 흐름을 점검합니다. 정상/오조립/가림을 실제로 판정할 별도 모델은 아직 추가 구현·평가가 필요합니다. 기존 실험 노트북과 결과 ZIP은 계속 보관하세요.

API 상세는01_API_V50_KO.md와 V46_01_API_FOR_TEAMMATE_KO.md를 참고하세요. 이전 V4.6 실행 명령 대신 반드시 이번02_start_server.ps1을 사용하세요.
