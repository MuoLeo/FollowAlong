# Completion error experiments

V50 실행 서비스와 분리된 실험 기록입니다. 이 디렉터리 추가로 HTTP API나 자동 오류 판별 기능이 활성화되지 않습니다.

| 폴더 | 목적 | 기록된 결과 |
|---|---|---|
| v56_normal_expansion | 정상 사진75장 보강 | 기존 자료 교차검증94.81%, 일반화 미확보 |
| v58_stage3_pairs | 새 Stage3 정상/오류 짝 영상 추가 | 새 촬영 오류6장 모두 미검출 |
| v59_component_diagnostic | 노란 블록/타이어 특정 부품 진단 | 색 기반 블록 유무 가능성, 타이어 실패 |

세부 범위는 [오류 판별 상태](../../../docs/completion/error_detection_status.md)를 참고합니다.
각 폴더의 `recorded_results/`는 실제 실행 결과를 보존합니다.
원본 사진/영상, 특징값과 모델은 포함하지 않습니다. 재현은 각 폴더 README의 데이터 복원 안내를 따르세요.
현재 통합 기준은 기존 V50이며 이 실험들을 서버에 연결하지 않습니다.
