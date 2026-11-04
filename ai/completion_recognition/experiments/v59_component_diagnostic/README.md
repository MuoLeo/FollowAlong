# v59_component_diagnostic — 오프라인 실험 기록

이 폴더는 실행 코드와 당시 평가 결과를 보존합니다. V50 HTTP 서버에 연결되지 않습니다.
`recorded_results/summary.json`과 CSV는 당시 결과이며 재실행 출력과 분리합니다.

## 재현용 데이터 복원

영상/사진/특징값/모델 바이너리는 Git에 넣지 않습니다.
별도로 전달된 `FollowAlong_V59_component_diagnostic.zip`을 다운로드한 뒤, 이 폴더에서 실행합니다.

```powershell
py -3.11 ..\restore_experiment_data.py --archive "$env:USERPROFILE\Downloads\FollowAlong_V59_component_diagnostic.zip" --experiment .
```

복원기는 `input_hashes.json`의 허용 목록과 SHA256을 확인해 데이터만 복원합니다.
원본 실험 ZIP의 Python/서버 코드는 덮어쓰지 않습니다.

복원 후 `py -3.11 -m pip install -r requirements.txt`와 `py -3.11 experiment.py`를 실행합니다. PyTorch/모델 ZIP은 필요 없습니다.
출력은 Git 제외 대상인 `results/`와 결과 ZIP에 생성됩니다.

## 범위

현재 기능/실패 사례/데모 범위는 저장소의 `docs/completion/error_detection_status.md`를 따릅니다.
독립적인 실시간 오류 판별 성능이나 배포 준비 상태를 의미하지 않습니다.
