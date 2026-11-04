# Model bundle — binaries distributed separately

다음4개 파일은 Git에 올리지 않고 `FollowAlong_V50_handoff.zip` 배포본에서 복원합니다.

| 파일 | 역할 |
|---|---|
| encoder_supcon.pt | 고정ResNet50 특징 추출 |
| temporal_final.pt | V4.7 candidate_new604 temporal head |
| stage_prototypes.pt | 목표단계prototype |
| rider_verifier.npz | Stage5탑승조건 |

`BUNDLE_MANIFEST.json`의SHA256과`POLICY_LOCK_BEFORE_TEST.json`으로실행모델을확인합니다. 정책metadata는Git에포함됩니다. 자동생성된GitHub Source code ZIP만다운로드하면모델바이너리는포함되지않습니다.

복원 명령은 부모 폴더README를 참고하세요. 복원한파일은 이폴더`.gitignore`규칙으로제외됩니다.
