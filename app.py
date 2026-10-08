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

# Gemini SDK 초기화
import google.generativeai as genai
if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
    genai.configure(api_key=GEMINI_API_KEY)


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
반드시 다음 6개 핵심 섹션을 구체적이고 실행 가능하게 작성하여, 순수한 JSON 객체(JSON Markdown 블록 없이 혹은 ```json 포함 가능)로 응답해 주세요.

필수 JSON 키:
1. "weekly_plan": 주차별 명확한 달성 목표 및 단계별 학습 전략 (마크다운 포맷 텍스트)
2. "daily_plan": 하루 시간대별 구체적인 실행 루틴 및 타임테이블 (마크다운 포맷 텍스트)
3. "review_cycle": 망각곡선 극복을 위한 주기별(당일, 3일차, 7일차, 14일차 등) 복습 매뉴얼 (마크다운 포맷 텍스트)
4. "quiz_items": 개념 이해도 및 취약 영역을 직접 테스트할 수 있는 자가 점검 문항 3~5개와 정답/해설 (마크다운 포맷 텍스트)
5. "checklist": 단계별 완수 여부를 체크할 수 있는 체크리스트 목록 (배열 형태의 문자열 목록 ["체크항목1", "체크항목2", ...])
6. "retrospective_guide": 매일 또는 매주 학습 효과를 극대화하기 위한 KPT(Keep/Problem/Try) 기반 회고 질문 가이드 (마크다운 포맷 텍스트)

답변은 반드시 유효한 JSON 형식이어야 합니다.
"""

    # 최신 Google Gemini 3.8 Flash 및 지원 모델군
    candidate_models = [
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-2.5-flash"
    ]
    last_error = None

    for model_name in candidate_models:
        try:
            logger.info(f"[Gemini] 모델 호출 시도 중: {model_name}")
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction
            )
            response = model.generate_content(
                prompt,
                generation_config={"temperature": 0.7, "max_output_tokens": 3000}
            )

            response_text = response.text.strip()
            # 마크다운 코드 블록 제거 처리 (```json ... ```)
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
            logger.warning(f"[Gemini] {model_name} 응답 JSON 파싱 실패, 원문 텍스트 구조화 시도: {jde}")
            # JSON 파싱 실패 시에도 마크다운 텍스트를 담아 반환
            fallback_dict = {
                "weekly_plan": response.text,
                "daily_plan": "상세 내용은 주간 계획 및 마크다운 전체보기를 참조하세요.",
                "review_cycle": "당일 복습(10분) -> 3일 후 누적 복습(30분) -> 주말 총정리를 준수하세요.",
                "quiz_items": "학습한 주요 개념을 백지에 스스로 설명해 보는 셀프 퀴즈를 진행하세요.",
                "checklist": ["1단계 기초 개념 정독", "2단계 핵심 문제 풀이", "3단계 오답노트 작성"],
                "retrospective_guide": "오늘 가장 잘 이해된 점(Keep), 어려웠던 점(Problem), 내일 개선할 점(Try)을 작성하세요."
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

        # genai 최신 키 동기화
        genai.configure(api_key=current_api_key)

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
