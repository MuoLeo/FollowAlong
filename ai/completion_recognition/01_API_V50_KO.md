# V5.0 연결 규격

기본 URL은 http://127.0.0.1:8767 입니다. 현재는 같은 컴퓨터에서만 접근합니다. HTTP body는 JSON이며 프레임은 JPEG/PNG의 base64입니다. 최대 body8MiB, 이미지12MP까지입니다. 이 개발 서버를 그대로 외부에 노출하지 않습니다.

| 시점 | API | 내용 |
|---|---|---|
| 최초 | POST /sessions | session_id, stage_id(1~5), stage_version(1부터) |
| 0.5초마다 | POST /sessions/{id}/frames | frame_id, captured_at_ms, stage_version, attempt_id, image_base64 |
| 완료 후보 후 외부 검사 결과 | POST /sessions/{id}/review | stage_version, candidate_event_id, verdict(valid/invalid/uncertain), request_id |
| 수정/가림 해소 후 재확인 | POST /sessions/{id}/retry | stage_version, attempt_id, captured_after_ms, request_id |
| 서버가 단계 변경을 확정할 때만 | POST /sessions/{id}/stage | stage_id, stage_version(이전+1), 마지막 종료는 stage_id:null |
| 동기화 | GET /sessions/{id} | 현재 stage/version/attempt/phase |
| 종료 | DELETE /sessions/{id} | 세션 제거 |

frame_id는 세션 전체에서 증가하는 정수, captured_at_ms는 같은 카메라 시간 기준의 촬영 시각(ms)입니다. 재시도하거나 단계가 바뀌어도 프레임 ID와 시계는 되돌리지 않습니다. 수신 시각을 넣지 않습니다. 0.5초 간격 허용 오차는75ms이며 누락/간격 이탈 시 버퍼를 초기화합니다.

초기 attempt_id는1, retry 응답에서 받은 새 값으로 이후 프레임을 보냅니다. 오래된 stage_version/attempt_id 또는 재확인 기준 시각보다 오래된 프레임은 거부됩니다. 같은 요청을 재전송할 때는 동일 ID와 payload를 사용합니다. 재생 이벤트는 event_id로 중복 제거합니다.

완료 후보 응답의 status는awaiting_review입니다. completion_score는 진행률이 아닙니다. Stage5 rider_probability는 탑승 존재 증거이며 일반 오류 정확도가 아닙니다. 계산하지 않은 경우 null입니다. rider_gate_passed:false는 완료 확정 보류이지 오류 판정이 아닙니다.

auto_advance:false를 유지합니다. 정상 검사의valid가 들어오면awaiting_stage_event이며 실제 단계 변경은 서버의stage 이벤트에만 따릅니다. 현재 서버에 자동 일반 오류 판정 모델이 없으므로 valid/invalid/uncertain은 외부 검사 또는 수동 검사 결과로만 제공합니다. 이 규격에서는 invalid를 AI가 스스로 만들지 않습니다.

03_replay_video.ps1은 **테스트 클라이언트가** valid와stage 이벤트를 흉내 냅니다. 제품 연결에서는 이 흉내를 제거하고 실제 서버 확정 이벤트로 대체하세요. 단계를3초마다 다시 보내는 설계가 아닙니다. 최초1회, 변경 확정 때1회입니다.
