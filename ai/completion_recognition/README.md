# FollowAlong Completion Recognition — V50

현재 목표 단계와0.5초 간격 사진을 받아 완료 후보를 반환하는 로컬 AI 서비스입니다. 기존 `ai/tutorial_analysis`와 독립된 모듈입니다. 팀의 Backend·Frontend를 자동으로 연결하거나 덮어쓰지 않습니다.

## 현재 범위

- 고정된 레고5단계의 stage-conditioned temporal 완료 후보 판단.
- 최근5프레임과3회 연속 확인,Stage5 탑승 조건 추가.
- HTTP JSON,세션·version·attempt 관리,수정·재검사·재생 이벤트.
- 일반 오조립·손 가림 자동 판정 모델은 아직 없습니다.
- 모델 score는 조립 진행률이 아닙니다. 실제 스마트폰·팀Backend 통합은 별도 검증이 필요합니다.

## 모델 복원

Git에는 모델 바이너리 대신 SHA256과 정책을 저장합니다. 팀이 배포한 `FollowAlong_V50_handoff.zip`을 GitHub Release 또는 전달 경로에서 다운로드하세요. 자동 생성된 GitHub Source code ZIP에는 모델이 없습니다.

저장소 루트의 Windows PowerShell에서:

```powershell
Set-Location .\ai\completion_recognition
py -3.11 .\restore_bundle.py --zip "$env:USERPROFILE\Downloads\FollowAlong_V50_handoff.zip"
py -3.11 .\verify_bundle.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\01_setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\02_start_server.ps1
```

다운로드한 ZIP의 실제 이름·위치가 다르면 `--zip` 경로를 수정하세요. 복원기는 Windows ZIP의역슬래시와 일반ZIP의슬래시 경로를 모두 처리하고,4개모델의 해시를 검사합니다. 추가 학습은 하지 않습니다.

Python3.11이 없으면 먼저 설치해야 합니다. 기존3.9/3.14를 삭제할 필요는 없습니다. 가상환경 활성화 없이 실행 스크립트가 해당 Python을 직접 사용합니다.

서버는 `http://127.0.0.1:8767`에서 실행됩니다. 같은 컴퓨터에서만 접근하며,실서비스 공개·인증·원격 연결은 별도 구성합니다.

## 영상 API 재생

서버를 켜둔 상태에서 새 터미널을 열고 이 모듈 폴더에서 실행합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\03_replay_video.ps1
```

`fullstage_val_02.mp4`는 별도로 확보해야 합니다.0.5초 예정 주기에 맞춘 재생은 다음과 같습니다.

```powershell
.\.venv\Scripts\python.exe -m followalong_v50.replay --simulate-external-approval --paced
```

위 테스트는 정상 검사 결과와Backend단계승인을 클라이언트가 흉내 냅니다. 실제 오류 모델의 정상 판단으로 설명하지 않습니다. 이미 평가한 영상의 재생은 통합 점검이며 새로운 독립 성능평가가 아닙니다.

## 테스트

이 모듈 폴더에서 실행합니다.

```powershell
py -3.11 -m unittest discover -s tests -v
```

프로토콜·상태 관리와 저장된 점수 재현 테스트는 모델 파일 없이 실행할 수 있습니다. 실제 checkpoint inference와 카메라 연결 검증을 대신하지 않습니다.

## 핵심 파일

| 경로 | 역할 |
|---|---|
| `followalong_v50/` | 현재 사용 진입점·완료 모델과Stage5조건 |
| `followalong_completion/` | 공통architecture·사진프로토콜 |
| `followalong_workflow/` | 수동/외부검사·수정·재검사상태 |
| `model_bundle/` | 정책·모델manifest; 복원된바이너리는Git제외 |
| `evaluation/` | 저장된영상02평가결과와점수fixture |
| `tests/` | 모델학습없이실행되는회귀검증 |
| `restore_bundle.py` | 배포ZIP에서모델4개복원 |

팀 연동 문서는 [Backend / Frontend 연동 명세](../../../docs/completion/backend_frontend_contract.md)를 참고하세요.

추가로 `01_API_V50_KO.md`, `00_START_HERE_KO.md`는 기존 단독패키지 기준 설명입니다. 명령을 실행할 작업 폴더는 이곳 `ai/completion_recognition`입니다. V51 비교 도구는 이번 V50 소스 묶음에 포함하지 않았습니다.
