# 튜토리얼 영상 분석 CLI

서버 없이 MP4 한 개를 분석하는 초기 실험 코드다. Whisper는 음성을 텍스트로 바꾸고 PySceneDetect는 장면 전환을 찾는다. 둘 다 의미 단위의 조립 단계를 보장하지 않으므로, 현재 출력은 반드시 사람이 검토하는 **규칙 기반 단계 후보**다. 생성형 AI나 조립 상태 모델은 아직 연결하지 않았다.

## 설치 (저장소 루트, Windows PowerShell)

```powershell
python -m venv ai/tutorial_analysis/.venv
ai/tutorial_analysis/.venv/Scripts/python.exe -m pip install -r ai/tutorial_analysis/requirements.txt
ffmpeg -version
ffprobe -version
```

Python 3.10 이상 환경에서 시작한다. FFmpeg의 ffmpeg.exe와 ffprobe.exe를 설치하고 해당 bin 폴더를 PATH에 추가한 뒤 새 터미널을 연다. 다운로드 안내: https://ffmpeg.org/download.html . 설치 스크립트가 전역 환경을 수정하지 않도록 가상환경을 사용한다. faster-whisper 자체 음성 디코딩은 별도 FFmpeg 실행 파일 없이 가능하지만, 이 CLI의 정규화·클립 생성에는 FFmpeg가 필요하다.

CPU/int8가 기본이다. 처음 Whisper를 실행하면 모델을 다운로드하므로 네트워크와 디스크 공간이 필요하다. CUDA는 공식 faster-whisper 문서의 CTranslate2/CUDA/cuDNN 호환성을 먼저 확인하고 사용한다. 설치 버전 범위는 API 호환을 위한 초기안이며 전체 잠금 파일은 실제 영상 점검 후 생성한다.

## 실행

```powershell
# 파일 경로 권장. 공백이나 한글이 있으면 따옴표로 감싼다.
ai/tutorial_analysis/.venv/Scripts/python.exe ai/tutorial_analysis/main.py "D:/videos/tutorial.mp4"

# 폴더 지정은 해당 폴더 바로 아래 MP4가 정확히 하나일 때만 가능하다.
ai/tutorial_analysis/.venv/Scripts/python.exe ai/tutorial_analysis/main.py "D:/videos/single-tutorial"

# 물리적인 단계별 MP4까지 생성한다.
ai/tutorial_analysis/.venv/Scripts/python.exe ai/tutorial_analysis/main.py "D:/videos/tutorial.mp4" --export-clips

# 음성 인식 없이 장면 탐지만 먼저 점검한다. 모델 다운로드가 없다.
ai/tutorial_analysis/.venv/Scripts/python.exe ai/tutorial_analysis/main.py "D:/videos/tutorial.mp4" --skip-speech

# 실험 설정 변경
ai/tutorial_analysis/.venv/Scripts/python.exe ai/tutorial_analysis/main.py "D:/videos/tutorial.mp4" --scene-threshold 35 --min-step 8 --pause 2 --language ko
```

입력 영상은 수정하지 않는다. 결과는 `storage/analysis/<실행ID>/`에 저장된다. `--output`으로 새 폴더를 지정할 수 있고 기존 폴더는 덮어쓰지 않는다. 실패 시 부분 산출물이 남으므로 다음 실행에는 새 경로를 사용한다. 이 결과는 Git에서 제외된다.

```text
playback.mp4       # 30 FPS로 정규화한 공통 타임라인
audio.wav         # 음성 인식을 수행한 경우
transcript.json   # 발화/단어 시각과 인식 텍스트
scenes.json       # 순수 장면 탐지 결과
steps.json        # 병합된 단계 후보, 경계 이유, 검토 필요 표시
clips/            # --export-clips 사용 시
```

JSON 시각은 모두 playback.mp4 기준이다. UI에서도 이 영상을 사용한다. 클립은 H.264/AAC로 재인코딩하므로 처리 시간이 추가된다. 음성 없는 영상은 장면 기반 결과만 만든다. 오디오가 있어도 음성 인식 실패는 성공으로 숨기지 않고 종료한다.

## 현재 단계 생성 규칙

1. 장면 전환 시각을 경계 후보로 얻는다.
2. Whisper 발화 사이에 1.5초 이상 공백이 있으면 다음 발화 시작을 후보로 삼는다. 이는 음향적 무음 검출이 아니라 ASR 타임스탬프 기반 휴지 추정이다.
3. 발화 시작에 '다음으로', '이제', '마지막으로' 등이 있으면 후보를 추가한다.
4. 장면 전환과 음성 후보가 2초 이내이면 음성 후보로 맞춘다.
5. 우선순위가 높은 후보부터 선택하고 5초 미만의 짧은 구간은 억제한다.
6. 경계가 없으면 전체 영상 하나를 유지한다. 길이를 맞추기 위해 임의로 자르지 않는다.

단어 시각은 향후 정밀 경계 조정용으로 저장하지만 현재 규칙은 발화 구간만 사용한다. 대표 이미지와 의미 있는 단계 제목은 아직 생성하지 않는다. 원문은 transcript_text로 보존하고 target_state_id는 null로 둔다. 클립 경계를 가로지르는 발화는 양쪽 후보에 포함되므로 원문 segment_id로 확인할 수 있다.

정적인 카메라로 찍은 조립 영상은 여러 작업이 있어도 장면 전환이 없을 수 있다. 반대로 화면 확대·손 이동·편집 전환은 조립 단계 변화가 아닐 수 있다. 이 때문에 장면 수와 단계 수를 동일하게 취급하면 안 된다.

## 파일 역할과 다음 실험

- main.py: 인자 검증과 실행 진입점
- pipeline.py: 미디어 처리, Whisper/PySceneDetect 호출, 파일 저장
- segmentation.py: 모델과 무관한 후보 결합 규칙
- tests/test_segmentation.py: 경계·중복·짧은 구간·경로 규칙 점검

먼저 1~3분짜리 음성 있는 영상 3개에 수동 정답 경계를 표시한다. scenes.json과 transcript.json을 따로 확인한 뒤 steps.json에서 과분할/누락/발화 잘림을 기록한다. 이후 언어 모델 또는 자막·프레임 기반 모델을 segmentation 위치에 추가해 의미 단계를 묶는 실험을 한다. 이미 저장한 자막과 장면을 재사용하는 입력 모드는 다음 개선 항목이다.

```powershell
python -m unittest discover -s ai/tutorial_analysis/tests -v
python ai/tutorial_analysis/main.py --help
```

위 단위 테스트는 외부 모델 없이 실행된다. 실제 FFmpeg 처리·장면 탐지·음성 인식 검증을 대신하지 않는다.

공식 문서:
- https://github.com/SYSTRAN/faster-whisper
- https://www.scenedetect.com/docs/latest/api.html
- https://www.scenedetect.com/docs/latest/api/detectors.html

