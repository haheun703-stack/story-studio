# 🚀 구글 AI(Gemini + Imagen 3) 동화책 완전 자동화 파이프라인

본 스크립트(`generate_fairytale_images.py`)는 구글의 **Gemini 1.5 Pro(텍스트)**와 **Vertex AI Imagen 3(이미지)**를 릴레이로 연동하여 동화책 일러스트를 한 번에 생성해주는 자동화 파이프라인입니다.

## 🛠 작동 원리 (3단계 워크플로우)

1. **[1단계] LLM으로 장면 분할**:  
   대본을 구글 `Gemini API`에 전달하여 의미 있는 씬으로 나누고 행동/배경만 분리해 깔끔한 JSON으로 받습니다.
2. **[2단계] 파이썬에서 프롬프트 조립 (DNA 융합)**:  
   추출한 행동/배경 데이터에 사용자가 미리 정의한 **[캐릭터 DNA]**와 **[스타일 DNA]**를 앞뒤로 결합합니다.
3. **[3단계] 이미지 일괄 생성**:  
   완성된 프롬프트를 구글 클라우드 `Vertex AI Imagen 3 API`로 전송하여 이미지를 생성하고 `output` 폴더에 자동 저장합니다.

## 📦 설치 및 실행 방법

1. **필수 라이브러리 설치**
   터미널을 열고 다음 명령어를 실행하세요.
   ```bash
   pip install -r requirements_auto.txt
   ```

2. **API 및 환경 설정 (.env)**
   동일한 폴더에 `.env` 파일을 만들고 아래 정보를 채워주세요. (구글 클라우드 세팅 필요)
   ```ini
   # 구글 AI Studio에서 발급받은 Gemini API 키
   GEMINI_API_KEY="AIzaSy..."
   
   # 구글 클라우드 플랫폼(GCP) 프로젝트 ID
   GCP_PROJECT_ID="your-gcp-project-id"
   
   # Imagen 3를 호출할 리전 (기본값: us-central1)
   GCP_LOCATION="us-central1"
   ```
   > **팁:** Vertex AI(Imagen)를 로컬에서 사용하려면 구글 클라우드 SDK가 설치되어 있어야 하며 터미널에서 `gcloud auth application-default login`을 통해 사용자 인증을 먼저 진행해야 합니다!

3. **스크립트 실행**
   스크립트 하단에 있는 `raw_story_text` 변수 안에 원하는 동화 대본을 붙여넣고 아래 명령어를 실행하세요.
   ```bash
   python generate_fairytale_images.py
   ```

## 💡 응용 및 커스터마이징

- `generate_fairytale_images.py` 파일 상단에 있는 **`CHARACTER_DNA`** 와 **`STYLE_DNA`** 변수를 본인만의 캐릭터 및 화풍 설정으로 자유롭게 변경해 보세요.
- Gemini, Claude 등 다른 텍스트 AI나 다른 이미지 생성 AI(Midjourney, Imagen 등)를 사용하고 싶다면, 해당 스크립트의 `analyze_story_to_scenes` 및 `generate_image_for_scene` 함수 안의 내용만 변경하시면 됩니다!
