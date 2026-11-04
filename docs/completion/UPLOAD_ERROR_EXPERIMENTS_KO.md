# 오류 실험 코드 추가 업로드

이 묶음은 기존 feat/completion-v50 브랜치에 추가하는 파일만 포함합니다.
V50 서버, 기존 모델/정책, 다른 조원 코드와 기존 문서는 덮어쓰지 않습니다.

1. GitHub 저장소에서 브랜치를 `feat/completion-v50`으로 선택합니다. main이 아님을 확인합니다.
2. 저장소 최상위(원래 ai/backend/frontend/docs가 보이는 위치)에서 파일 업로드 화면을 엽니다.
3. 이 ZIP을 풀면 나오는 `ai`, `docs` 두 폴더를 함께 끌어놓습니다. ZIP 자체를 올리지 않습니다.
4. 경로가 `ai/completion_recognition/experiments/...`와 `docs/completion/...`로 시작하는지 확인합니다.
5. 커밋 메시지: `docs(ai): preserve error detection experiments and evaluation limits`
6. 현재 feat/completion-v50 브랜치에 커밋합니다. 아직 main으로 병합하지 않습니다.
7. 해당 브랜치에서 experiments와 error_detection_status.md가 보이는지 확인합니다.

가중치/영상/사진/특징값/가상환경을 추가로 끌어놓지 않습니다.
현재 묶음은 기록 보존 목적입니다. 자동 오조립 판별 서비스가 완성됐다고 전달하지 않습니다.
모델 실행 파일은 기존 FollowAlong_V50_handoff.zip, 재현 데이터는 별도로 전달된 실험 ZIP을 사용합니다.

Git clone한 로컬 저장소를 사용하는 경우에는 이 묶음의 ai/docs를 저장소 루트에 복사한 뒤,
feat/completion-v50 브랜치에서 아래 두 경로의 변경만 확인하고 커밋/푸시합니다.
- ai/completion_recognition/experiments
- docs/completion/error_detection_status.md 및 이 업로드 안내
ZIP으로 받은 폴더에는 .git이 없으므로 그 안에서 임의로 git init해 새 저장소를 만들지 않습니다.
