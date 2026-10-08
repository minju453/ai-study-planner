import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import requests

# 1. 환경변수(.env) 로드
load_dotenv()

# 2. 백엔드 로깅 설정 (초보자 친화적인 로그 포맷)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("StudyPlanner")

# 3. Flask 앱 초기화 (서버리스 환경 경로 보장)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

# Vercel Serverless PATH_INFO 정규화 미들웨어
class VercelPathMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        for prefix in ("/api/index", "/api"):
            if path == prefix:
                environ["PATH_INFO"] = "/"
                break
            elif path.startswith(prefix + "/"):
                environ["PATH_INFO"] = path[len(prefix):]
                break
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathMiddleware(app.wsgi_app)

# 4. API 키 가져오기
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()

# Gemini SDK 초기화 (gRPC 블로킹 방지를 위해 transport='rest' 명시)
import google.generativeai as genai
if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
    genai.configure(api_key=GEMINI_API_KEY, transport="rest")


def search_web_serper(query):
    """
    Serper.dev API를 활용하여 최신 시험 정보나 학습 자료를 웹 검색합니다.
    """
    if not SERPER_API_KEY or SERPER_API_KEY == "your_serper_api_key_here":
        logger.info("[Serper] API 키가 설정되지 않아 웹 검색을 건너뜁니다.")
        return None

    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "q": query,
        "gl": "kr",
        "hl": "ko"
    }

    try:
        logger.info(f"[Serper] 웹 검색 요청 중: '{query}'")
        response = requests.post(url, headers=headers, json=payload, timeout=8)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("organic", [])[:3]:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                results.append(f"- 제목: {title}\n  요약: {snippet}\n  출처: {link}")
            if results:
                logger.info(f"[Serper] 웹 검색 결과 {len(results)}건 수집 완료")
                return "\n".join(results)
        else:
            logger.warning(f"[Serper] API 응답 에러 (코드: {response.status_code})")
    except Exception as e:
        logger.warning(f"[Serper] 웹 검색 중 예외 발생: {str(e)}")

    return None


def call_gemini_planner(goal, exam_date, current_level, daily_time, weakness, preferred_style, web_context=None):
    """
    Gemini API를 호출하여 6가지 핵심 영역이 담긴 맞춤형 학습 플랜을 생성합니다.
    요청된 gemini-3.5-flash 및 가용 모델 자동 폴백을 지원합니다.
    """
    # 프롬프트 엔지니어링: 6가지 필수 섹션을 명확한 JSON 구조로 요청
    system_instruction = (
        "당신은 대한민국 최고의 학습 컨설턴트이자 수험 전략 전문가입니다. "
        "학습자의 조건(목표, 시험일, 수준, 가용시간, 취약점, 선호방식)을 심층 분석하여 "
        "가장 현실적이면서도 효율적인 초개인화 학습 계획을 수립해야 합니다."
    )

    prompt = f"""
[학습자 프로필]
- 학습 목표 및 대상 시험: {goal}
- 목표 시험일 / 완료일: {exam_date}
- 현재 학습자 수준: {current_level}
- 하루 투입 가능 시간: {daily_time}
- 집중 보완 취약 영역: {weakness if weakness else '전반적인 기본기 및 핵심 개념'}
- 선호하는 학습 방식: {preferred_style if preferred_style else '이론과 실전문제를 균형있게 학습'}
"""

    if web_context:
        prompt += f"""
[최신 웹 검색 참조 자료 (Serper.dev)]
{web_context}
(위 최신 시험 정보와 출제 트렌드를 플랜 수립에 적극 반영해 주세요.)
"""

    prompt += """
[작성 요청사항]
반드시 다음 6개 핵심 섹션을 완성도 높고 깔끔하게 작성하여 유효한 JSON으로 응답해 주세요.

필수 JSON 키 및 작성 형식:
1. "weekly_plan": 시험일까지의 주차별 학습 로드맵 (반드시 아래의 정돈된 마크다운 포맷으로 작성):
   ### 📌 1주차: [핵심 테마 및 목표]
   - **학습 범위:** 구체적인 단원 및 이론 범위
   - **실행 과제:** 개념 정독 및 기본 예제 풀이
   - **주간 목표치:** 주말 기준 달성해야 할 성취 기준
   
   ### 📌 2주차: [심화 및 기출 정복]
   - **학습 범위:** 기출 빈출 유형 및 취약 파트 집중 공략
   - **실행 과제:** 회차별 기출문제 풀이 및 오답노트
   - **주간 목표치:** 모의고사 목표 점수 달성
   (시험일까지 주차별로 깔끔하게 정리)

2. "daily_plan": 하루 일과 시간대별(오전/오후/저녁) 루틴 및 타임테이블 (마크다운)
3. "review_cycle": 에빙하우스 망각곡선 기반 복습 주기표(당일 10분, 3일 후 30분, 7일 후 누적 정리 등) (마크다운)
4. "quiz_items": 개념 확인 및 취약점 셀프 점검 퀴즈 3~5문항과 정답/해설 (마크다운)
5. "checklist": 단계별 체크리스트 배열 (["1주차 기본 개념 완독", "핵심 기출 3개년 풀이", "오답노트 1회독", ...])
6. "retrospective_guide": KPT(Keep/Problem/Try) 프레임워크 기반 일일/주간 학습 회고 가이드 (마크다운)
"""

    # 최신 Google Gemini 3.8 Flash 및 가용 모델군 (자동 즉시 폴백)
    candidate_models = [
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest"
    ]
    last_error = None

    for model_name in candidate_models:
        try:
            logger.info(f"[Gemini] 모델 호출 시도 중: {model_name}")
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction
            )
            # 구조화된 순수 JSON 출력을 강제하여 파싱 실패 및 텍스트 깨짐 원천 방지
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.5,
                    "max_output_tokens": 4000,
                    "response_mime_type": "application/json"
                },
                request_options={"timeout": 25}
            )

            response_text = response.text.strip()
            # 혹시 마크다운 블록이 포함되어 있을 경우 정제
            if response_text.startswith("```"):
                lines = response_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_text = "\n".join(lines).strip()

            parsed_data = json.loads(response_text)
            logger.info(f"[Gemini] 플랜 생성 성공 (사용 모델: {model_name})")
            return parsed_data, model_name

        except json.JSONDecodeError as jde:
            logger.warning(f"[Gemini] {model_name} 응답 JSON 파싱 실패, 정규식 구조화 시도: {jde}")
            try:
                # 텍스트 내에서 JSON 중괄호 영역만 추출 시도
                import re
                json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
                if json_match:
                    parsed_data = json.loads(json_match.group(0))
                    return parsed_data, model_name
            except Exception:
                pass

            # 최후의 fallback: raw 텍스트 대신 깔끔한 안내 구조화
            fallback_dict = {
                "weekly_plan": "### 📌 주간 학습 로드맵\n" + response.text.split('"daily_plan"')[0].replace('{"weekly_plan":', '').strip(' "\n,'),
                "daily_plan": "### ⏰ 일일 학습 루틴\n- **기상/오전:** 전날 학습한 핵심 개념 10분 가볍게 복습\n- **집중 공부 시간:** 핵심 이론 정독 및 필수 유형 문제 풀이\n- **마무리:** 오늘 학습한 내용 셀프 퀴즈 및 오답 정리",
                "review_cycle": "### 🔄 에빙하우스 복습 주기\n1. **당일 10분 복습:** 잠들기 전 오늘 배운 핵심 키워드 인출\n2. **3일차 30분 복습:** 취약 파트 및 오답 문제 재풀이\n3. **7일차 누적 복습:** 한 주간의 학습 내용 총정리 모의테스트",
                "quiz_items": "### 📝 자가 점검 퀴즈\n- **Q1.** 오늘 학습한 가장 중요한 핵심 개념 3가지를 백지에 적을 수 있는가?\n- **Q2.** 자주 틀리는 유형의 풀이 알고리즘을 타인에게 설명할 수 있는가?\n*(정답과 해설은 기본서 및 요약 노트를 참조하세요)*",
                "checklist": ["1단계 기초 개념 및 핵심 이론 완독", "2단계 기출 유형별 문제 풀이", "3단계 오답노트 작성 및 취약점 보완"],
                "retrospective_guide": "### 💡 KPT 학습 회고 가이드\n- **Keep (유지할 점):** 오늘 시간 관리가 잘 된 부분은 무엇인가?\n- **Problem (개선할 점):** 집중이 흐트러졌거나 어려웠던 개념은 무엇인가?\n- **Try (시도할 점):** 내일 더 효율적으로 학습하기 위한 실천 행동 1가지"
            }
            return fallback_dict, model_name

        except Exception as e:
            logger.warning(f"[Gemini] {model_name} 호출 중 에러 발생: {str(e)}")
            last_error = e
            continue

    raise RuntimeError(f"모든 Gemini 모델 호출에 실패했습니다: {last_error}")


@app.route("/", methods=["GET", "POST"])
@app.route("/api", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def index():
    """메인 학습 플래너 페이지 렌더링 (POST 요청 시 generate로 자동 연계)"""
    if request.method == "POST":
        return generate()
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
@app.route("/api/generate", methods=["POST"])
@app.route("/api/index/generate", methods=["POST"])
def generate():
    """학습 계획 생성 API 엔드포인트"""
    try:
        data = request.get_json()
        if not data:
            logger.error("[요청 오류] 빈 요청 데이터")
            return jsonify({"status": "error", "message": "요청 데이터가 올바르지 않습니다."}), 400

        # 1. 입력값 검증 (초보자 친화적 메시지)
        goal = data.get("goal", "").strip()
        exam_date = data.get("exam_date", "").strip()
        current_level = data.get("current_level", "").strip()
        daily_time = data.get("daily_time", "").strip()
        weakness = data.get("weakness", "").strip()
        preferred_style = data.get("preferred_style", "").strip()
        use_web_search = bool(data.get("use_web_search", False))

        logger.info(f"[요청 수신] 목표: '{goal}', 시험일: '{exam_date}', 수준: '{current_level}', 가능시간: '{daily_time}'")

        if not goal or len(goal) > 100:
            return jsonify({"status": "error", "message": "학습 목표를 1~100자 사이로 입력해 주세요."}), 400
        if not exam_date or len(exam_date) > 50:
            return jsonify({"status": "error", "message": "목표 시험일 또는 완료일을 올바르게 지정해 주세요."}), 400
        if not current_level or len(current_level) > 100:
            return jsonify({"status": "error", "message": "현재 학습 수준을 올바르게 선택해 주세요."}), 400
        if not daily_time or len(daily_time) > 100:
            return jsonify({"status": "error", "message": "하루 공부 가능 시간을 100자 이내로 입력해 주세요."}), 400
        if len(weakness) > 200:
            return jsonify({"status": "error", "message": "취약 파트 내용은 200자 이내로 입력해 주세요."}), 400
        if len(preferred_style) > 100:
            return jsonify({"status": "error", "message": "학습 스타일 내용은 100자 이내로 입력해 주세요."}), 400

        # API Key 유효성 체크
        current_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not current_api_key or current_api_key == "your_gemini_api_key_here":
            logger.error("[설정 오류] GEMINI_API_KEY 미설정")
            return jsonify({
                "status": "error",
                "message": "서버에 GEMINI_API_KEY 환경변수가 설정되지 않았습니다. 관리자 설정을 확인해 주세요."
            }), 500

        # genai 최신 키 동기화 (transport='rest'로 gRPC 블로킹 방지)
        genai.configure(api_key=current_api_key, transport="rest")

        # 2. 웹 검색 옵션 실행 (Serper API)
        web_context = None
        if use_web_search:
            search_query = f"{goal} 시험범위 출제경향 공부방법"
            web_context = search_web_serper(search_query)

        # 3. Gemini 플래너 호출
        plan_result, used_model = call_gemini_planner(
            goal=goal,
            exam_date=exam_date,
            current_level=current_level,
            daily_time=daily_time,
            weakness=weakness,
            preferred_style=preferred_style,
            web_context=web_context
        )

        # 4. 다운로드 및 복사용 전체 마크다운 텍스트 조합
        checklist_md = "\n".join([f"- [ ] {item}" for item in plan_result.get("checklist", [])])
        full_markdown = f"""# 🎯 맞춤형 AI 학습 플래너
> **목표:** {goal} | **목표일:** {exam_date}  
> **현재 수준:** {current_level} | **일일 가용 시간:** {daily_time}  
> **생성일자:** {datetime.now().strftime('%Y-%m-%d %H:%M')} (엔진: {used_model})

---

## 1. 📅 주간 학습 계획 (Weekly Plan)
{plan_result.get('weekly_plan', '')}

---

## 2. ⏰ 일일 루틴 및 계획 (Daily Schedule)
{plan_result.get('daily_plan', '')}

---

## 3. 🔄 에빙하우스 복습 주기 매뉴얼 (Review Cycle)
{plan_result.get('review_cycle', '')}

---

## 4. 📝 자가 점검 퀴즈 및 해설 (Quiz & Check)
{plan_result.get('quiz_items', '')}

---

## 5. ✅ 단계별 진도 체크리스트 (Progress Checklist)
{checklist_md}

---

## 6. 💡 KPT 학습 회고 가이드 (Retrospective Guide)
{plan_result.get('retrospective_guide', '')}
"""

        logger.info(f"[생성 완료] 성공적으로 6개 섹션 응답 반환 (모델: {used_model})")

        return jsonify({
            "status": "success",
            "model": used_model,
            "data": plan_result,
            "full_markdown": full_markdown
        })

    except Exception as e:
        logger.error(f"[서버 에러] 플랜 생성 중 오류 발생: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "학습 플랜을 생성하는 중 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
        }), 500


if __name__ == "__main__":
    is_debug = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")
    logger.info("=== AI 학습 플래너 웹앱 서버를 시작합니다 ===")
    logger.info("접속 주소: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=is_debug)
