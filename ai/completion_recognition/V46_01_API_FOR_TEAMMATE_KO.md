# V4.6 통합 규격

목표 단계의 소유자는 기존과 같이 외부 서버입니다. 완료 후보가 다음 단계를 자동 선택하지 않습니다. 서버는 처음 시작과 단계 전환 때만 stage 이벤트를 보냅니다.

원본 V4.3와 별도 실행: 기본 주소 http://127.0.0.1:8766 . 세션은 단일 프로세스 메모리 상태입니다.

## 상태 순서

active → [5장 history + 2연속 positive] → awaiting_review

외부 review valid → awaiting_stage_event → 외부 stage 이벤트 → active

외부 review invalid → correction_wait (+ replay_stage_video 이벤트 1개) → 사용자가 다시 확인 → active (이전 history 삭제)

외부 review uncertain → needs_clear_view (재생 이벤트 없음) → 사용자가 다시 확인 → active

수정 대기에도 사진을 보내도 됩니다. 시간·ID는 기록하지만 encoder를 다시 호출하지 않습니다. 다음 판단에는 retry 이후 새 사진만 사용합니다.

## 공통

- `session_id`: 촬영 세션 고유 ID. 사용자/카메라마다 분리.
- `stage_id`: 1~5, 종료 이벤트는 null.
- `stage_version`: 단계 이벤트 때 +1. 같은 ID·version 재전송은 멱등.
- `attempt_id`: 최초1, 같은 단계 재검사 때 +1. 새 단계에서는1. 최신 응답을 촬영자에게 동기화.
- `frame_id`: 세션 전체에서 계속 증가. 재검사해도 0으로 되돌리지 않음.
- `captured_at_ms`: 공통 카메라 촬영 시계 기준. 재검사해도 시계 초기화 금지. 네트워크 도착 시간이 아님.

## 요청

POST /sessions
```json
{"session_id":"demo1","stage_id":3,"stage_version":1}
```

POST /sessions/demo1/frames (0.5초마다)
```json
{"frame_id":10,"captured_at_ms":5000,"stage_version":1,"attempt_id":1,"image_base64":"..."}
```
완료 후보는 status=awaiting_review, candidate_event_id를 반환합니다. 외부 validator가 없으면 자동 정상/오류 판정하지 말고 수동 확인 상태로 표시해야 합니다.

POST /sessions/demo1/review (신뢰하는 외부 서버 또는 수동 판정만)
```json
{"stage_version":1,"candidate_event_id":"demo1:1:10","verdict":"invalid","request_id":"review-unique-001"}
```
verdict=valid/invalid/uncertain. invalid에만 action={type:replay_stage_video,event_id,stage_id,stage_version,attempt_id} 반환. 프론트/외부 서버는 event_id와 현재 stage_version/attempt_id를 검사해 같은 이벤트를 한 번만 적용해야 합니다. HTTP 재전송 시 동일 request_id를 재사용하며, 동일 응답이 다시 와도 영상 재생을 반복하지 않습니다. 초기 중복 방지는 로컬 Set으로 시연하며 실제 앱은 페이지 재접속에도 처리 내역을 유지하도록 저장해야 합니다.

GET /sessions/demo1 은 현재 상태 조회만 하며 action을 재발행하지 않습니다.

POST /sessions/demo1/retry
```json
{"stage_version":1,"attempt_id":1,"captured_after_ms":8000,"request_id":"retry-unique-001"}
```
사용자가 수정 완료/다시 확인을 눌렀을 때 호출. captured_after_ms는 버튼 시점에 촬영자와 공유하는 시계의 값입니다. 응답 attempt_id=2를 촬영자에게 먼저 전달하고 이전 attempt의 대기 전송을 버립니다. 새 시각보다 뒤에 촬영한 사진부터 전송합니다. 5장 history와 연속 판정 수, candidate를 삭제합니다. 늦게 온 이전 attempt 사진과 이전 review는409. retry 재전송은 같은 request_id로 멱등 처리.

POST /sessions/demo1/stage
```json
{"stage_id":4,"stage_version":2}
```
정상 확인 후 외부 서버가 웹페이지와 AI 단계 동기화 시 호출. AI가 자체 증가시키지 않습니다. 정상 완료 흐름은 기존대로 직전 단계 history를 유지하되, retry에서는 history를 완전히 비웁니다.

DELETE /sessions/demo1 : 세션 종료.

## 실제 앱 반영 시 구분

이 코드는 수정 대기 프로토콜을 구현합니다. 실제 조립 오류, 손 가림, 손을 뗐는지 여부는 자동 판단하지 않습니다. demo 버튼만으로 판정을 흉내 냅니다. 카메라/조원 서버/프로덕션 프론트 통합은 별도입니다.
