# 🎯 AI 맞춤형 학습 플래너 (AI Study Planner)

> **"Vintage Poster & Retro Cutout Collage Edition"**  
> Google Gemini 3.8 Flash AI와 Serper.dev 최신 웹 검색 엔진을 결합하여, 학습자의 조건에 맞춘 초개인화 수험 전략과 망각 방지 복습 루틴을 발행하는 풀스택 웹 애플리케이션입니다.

---

## ✨ 핵심 기능

1. **초개인화 프로필 분석**:
   - 학습 목표, 목표 시험일, 현재 수준, 하루 가능 시간, 집중 보완 취약 영역, 선호 학습 방식을 종합 분석
2. **최신 시험 정보 실시간 웹검색 연동 (Serper.dev)**:
   - 최신 출제 트렌드 및 시험 범위를 검색하여 학습 계획에 즉시 반영
3. **6대 핵심 솔루션 제공 (Gemini 3.8 Flash)**:
   - 📅 **주간 학습 전략 (Weekly Roadmap)**: 주차별 명확한 달성 목표 및 단계별 로드맵
   - ⏰ **일일 실행 루틴 (Daily Routine)**: 하루 시간대별 초집중 타임테이블
   - 🔄 **망각 방지 매뉴얼 (Review Cycle)**: 에빙하우스 망각곡선 극복 주기별 복습법
   - 📝 **자가 진단 퀴즈 (Pop Quiz)**: 취약점 확인용 셀프 체크 테스트 & 상세 해설
   - ✅ **인터랙티브 완주 체크리스트**: 실시간 진도율(%) 계산 게이지 바 연동
   - 💡 **성장 회고 가이드 (KPT Retrospective)**: Keep / Problem / Try 기반 회고
4. **편의 기능**:
   - 전체 플랜 원클릭 클립보드 복사
   - 마크다운(`.md`) 파일 즉시 다운로드
5. **감각적인 90년대 빈티지 포스터 UI**:
   - 로열 블루 하프톤 도트 배경 & 부유하는 레트로 스타버스트 스티커
   - 마스킹 테이프, 페이퍼 컷아웃, 볼드 3D 팝 버튼 애니메이션

---

## 🛠️ 기술 스택 (Tech Stack)

- **Backend**: Python 3.14, Flask, python-dotenv, requests
- **AI Engine**: Google Gemini API (`gemini-3.8-flash`)
- **Search Engine**: Serper.dev Search API
- **Frontend**: HTML5, Modern CSS3 (Retro Cutout Theme), Vanilla JavaScript (ES6+), marked.js
- **Version Control**: Git & GitHub

---

## 📁 프로젝트 구조

```text
ai-study-planner/
├── app.py                     # Flask 백엔드 서버 및 Gemini/Serper API 연동 로직
├── requirements.txt           # 파이썬 패키지 의존성 목록
├── .env.example               # 환경변수 설정 가이드 템플릿
├── .gitignore                 # 보안 및 불필요 파일 제외 설정 (.env, venv 등)
├── README.md                  # 프로젝트 설명서
├── templates/
│   └── index.html             # 레트로 빈티지 포스터 메인 웹 화면
└── static/
    ├── css/
    │   └── style.css          # 레트로 팝 컷아웃 & 마스킹 테이프 스타일시트
    └── js/
        └── app.js             # 비동기 통신, 마크다운 렌더링, 체크리스트 로직
```

---

## 🚀 빠른 시작 가이드 (Quick Start)

### 1. 가상환경 활성화 및 패키지 설치
```powershell
# 가상환경 활성화
.\venv\Scripts\Activate.ps1

# 필수 패키지 설치
py -m pip install -r requirements.txt
```

### 2. 환경변수(.env) 설정
프로젝트 루트 경로에 `.env` 파일을 생성하고 발급받은 API 키를 입력합니다:
```env
GEMINI_API_KEY=your_gemini_api_key_here
SERPER_API_KEY=your_serper_api_key_here
```
> - Gemini API Key: [Google AI Studio](https://aistudio.google.com/)에서 무료 발급
> - Serper API Key (선택): [Serper.dev](https://serper.dev/)에서 무료 발급

### 3. 애플리케이션 실행
```powershell
py app.py
```
브라우저에서 `http://127.0.0.1:5000`으로 접속하여 맞춤형 플래너를 생성하세요!

---

## 📄 라이선스
MIT License
