FollowAlong 타임라인 편집 기능 적용 방법

포함 파일
1. edit.html
   - 기존 edit.html을 이 파일로 교체합니다.
2. EDIT_PAGE_script_section.js
   - 기존 script.js에서 // EDIT PAGE 주석부터 해당 편집 페이지 블록의 끝까지를 이 파일 내용으로 교체합니다.
   - script.js의 업로드, Connect, Mobile 관련 코드는 삭제하거나 교체하지 말고 그대로 둡니다.
3. timeline_style_additions.css
   - 기존 style.css 맨 아래에 전체 내용을 추가합니다.

동작
- 타임라인 구간 더블클릭: 해당 구간 하나를 둘로 분할합니다.
- 경계선 드래그: 양쪽 단계의 시간 경계를 함께 이동합니다.
- 경계선 선택 후 삭제 버튼 또는 Delete 키: 양쪽 단계를 하나로 합칩니다.
- 최소 단계 길이: 1초
- 마지막 단계는 영상의 실제 종료 시간에 맞춥니다.
- 단계 시작/종료 시간은 타임라인 조작에 맞춰 목록에 자동 반영됩니다.

주의
현재 대화에서 확인 가능한 script.js는 EDIT PAGE 부분만 제공되어 있습니다.
따라서 전체 script.js를 새 파일로 덮어쓰지 않도록 편집 페이지 코드만 별도 파일로 제공합니다.
