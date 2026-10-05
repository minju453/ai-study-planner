/**
 * AI 맞춤형 학습 플래너 프론트엔드 스크립트 (app.js)
 * - 폼 유효성 검사 및 서버 비동기(/generate) 통신
 * - 로딩 애니메이션 및 오류 처리
 * - 마크다운 렌더링 및 인터랙티브 체크리스트
 * - 전체 복사 및 .md 파일 다운로드
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. DOM 요소 취득
    const plannerForm = document.getElementById("plannerForm");
    const submitBtn = document.getElementById("submitBtn");
    const btnText = submitBtn.querySelector(".btn-text");
    const btnSpinner = submitBtn.querySelector(".btn-spinner");
    const alertBox = document.getElementById("alertBox");
    const alertMessage = document.getElementById("alertMessage");

    const emptyState = document.getElementById("emptyState");
    const loadingState = document.getElementById("loadingState");
    const resultContent = document.getElementById("resultContent");

    const engineBadge = document.getElementById("engineBadge");
    const copyAllBtn = document.getElementById("copyAllBtn");
    const downloadMdBtn = document.getElementById("downloadMdBtn");

    const secWeeklyPlan = document.getElementById("secWeeklyPlan");
    const secDailyPlan = document.getElementById("secDailyPlan");
    const secReviewCycle = document.getElementById("secReviewCycle");
    const secQuizItems = document.getElementById("secQuizItems");
    const checklistContainer = document.getElementById("checklistContainer");
    const progressBarFill = document.getElementById("progressBarFill");
    const progressText = document.getElementById("progressText");
    const secRetrospective = document.getElementById("secRetrospective");

    // 전역 상태 변수
    let currentFullMarkdown = "";
    let currentGoalName = "학습플랜";

    // 오늘 날짜를 시험일 min 속성에 기본 세팅 (과거 날짜 선택 방지)
    const todayStr = new Date().toISOString().split("T")[0];
    const examDateInput = document.getElementById("examDate");
    if (examDateInput) {
        examDateInput.min = todayStr;
    }

    // 2. 알림창 표시/숨김 헬퍼 함수
    function showAlert(message) {
        alertMessage.textContent = message;
        alertBox.classList.remove("hidden");
        alertBox.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    function hideAlert() {
        alertBox.classList.add("hidden");
        alertMessage.textContent = "";
    }

    // 3. 폼 제출 이벤트 리스너
    plannerForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        hideAlert();

        // 폼 입력값 취득
        const goal = document.getElementById("goal").value.trim();
        const examDate = document.getElementById("examDate").value.trim();
        const currentLevel = document.getElementById("currentLevel").value.trim();
        const dailyTime = document.getElementById("dailyTime").value.trim();
        const weakness = document.getElementById("weakness").value.trim();
        const preferredStyle = document.getElementById("preferredStyle").value.trim();
        const useWebSearch = document.getElementById("useWebSearch").checked;

        // 클라이언트 사이드 입력값 유효성 검사 (초보자 친화적 알림)
        if (!goal) {
            showAlert("학습 목표 또는 시험명을 입력해 주세요. (예: 정보처리기사 실기)");
            document.getElementById("goal").focus();
            return;
        }

        if (!examDate) {
            showAlert("목표 시험일 또는 완주 마감일을 선택해 주세요.");
            document.getElementById("examDate").focus();
            return;
        }

        if (!currentLevel) {
            showAlert("현재 본인의 학습 수준을 선택해 주세요.");
            document.getElementById("currentLevel").focus();
            return;
        }

        if (!dailyTime) {
            showAlert("하루에 공부할 수 있는 시간을 입력해 주세요. (예: 평일 2시간)");
            document.getElementById("dailyTime").focus();
            return;
        }

        // 로딩 UI 상태 전환
        setLoadingState(true);

        const payload = {
            goal: goal,
            exam_date: examDate,
            current_level: currentLevel,
            daily_time: dailyTime,
            weakness: weakness,
            preferred_style: preferredStyle,
            use_web_search: useWebSearch
        };

        try {
            console.log("[요청 전송]", payload);
            const response = await fetch("/generate", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            let result = null;
            const rawText = await response.text();
            try {
                result = JSON.parse(rawText);
            } catch (jsonErr) {
                console.warn("[응답 JSON 파싱 실패 - 비정상 응답]", rawText);
            }

            if (!response.ok || !result || result.status !== "success") {
                let errMsg = "학습 플랜을 생성하지 못했습니다.";
                if (result && result.message) {
                    errMsg = result.message;
                } else if (response.status === 504) {
                    errMsg = "AI 답변 생성 시간이 초과되었습니다 (504). 잠시 후 다시 시도해 주세요.";
                } else if (response.status === 500) {
                    errMsg = "서버 AI 설정 또는 API 키 연결 오류가 발생했습니다 (500).";
                } else {
                    errMsg = `서버 응답 오류 (코드: ${response.status}). 잠시 후 다시 시도해 주세요.`;
                }
                showAlert(errMsg);
                setLoadingState(false, false);
                return;
            }

            // 성공 시 결과 렌더링
            currentGoalName = goal.replace(/[^a-zA-Z0-9가-힣]/g, "_");
            renderPlanResult(result);
            setLoadingState(false, true);

        } catch (error) {
            console.error("[네트워크 또는 통신 오류]", error);
            showAlert("네트워크 연결이 불안정하거나 일시적인 통신 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.");
            setLoadingState(false, false);
        }
    });

    // 4. 로딩 상태 제어 함수
    function setLoadingState(isLoading, isSuccess = false) {
        if (isLoading) {
            submitBtn.disabled = true;
            btnText.textContent = "AI 플랜 설계 중...";
            btnSpinner.classList.remove("hidden");

            emptyState.classList.add("hidden");
            resultContent.classList.add("hidden");
            loadingState.classList.remove("hidden");
        } else {
            submitBtn.disabled = false;
            btnText.textContent = "✨ AI 맞춤형 학습 플랜 생성하기";
            btnSpinner.classList.add("hidden");
            loadingState.classList.add("hidden");

            if (isSuccess) {
                resultContent.classList.remove("hidden");
                emptyState.classList.add("hidden");
                // 결과 영역으로 스무스 스크롤
                resultContent.scrollIntoView({ behavior: "smooth", block: "start" });
            } else {
                emptyState.classList.remove("hidden");
                resultContent.classList.add("hidden");
            }
        }
    }

    // 5. 생성된 결과 렌더링 함수
    function renderPlanResult(response) {
        const data = response.data || {};
        currentFullMarkdown = response.full_markdown || "";

        // 엔진 배지 표기
        engineBadge.textContent = response.model || "Gemini 3.5 Flash";

        // 6대 섹션 마크다운 렌더링 (marked.js 활용)
        const parseMd = (text) => {
            if (!text) return "<p>내용이 제공되지 않았습니다.</p>";
            return typeof marked !== "undefined" ? marked.parse(text) : `<pre>${text}</pre>`;
        };

        secWeeklyPlan.innerHTML = parseMd(data.weekly_plan);
        secDailyPlan.innerHTML = parseMd(data.daily_plan);
        secReviewCycle.innerHTML = parseMd(data.review_cycle);
        secQuizItems.innerHTML = parseMd(data.quiz_items);
        secRetrospective.innerHTML = parseMd(data.retrospective_guide);

        // 5번 섹션: 인터랙티브 체크리스트 생성
        renderInteractiveChecklist(data.checklist || []);
    }

    // 6. 인터랙티브 체크리스트 및 진도율 계산기
    function renderInteractiveChecklist(items) {
        checklistContainer.innerHTML = "";

        if (!items || items.length === 0) {
            checklistContainer.innerHTML = "<li>체크리스트 항목이 없습니다.</li>";
            updateProgress(0, 0);
            return;
        }

        items.forEach((itemText, idx) => {
            const li = document.createElement("li");
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.id = `chk_${idx}`;

            const label = document.createElement("label");
            label.htmlFor = `chk_${idx}`;
            label.textContent = itemText;

            // 체크박스 클릭 시 스타일 및 진도율 갱신
            checkbox.addEventListener("change", () => {
                if (checkbox.checked) {
                    li.classList.add("checked");
                } else {
                    li.classList.remove("checked");
                }
                calculateProgress();
            });

            // li 전체를 클릭해도 체크 토글
            li.addEventListener("click", (e) => {
                if (e.target !== checkbox && e.target !== label) {
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event("change"));
                }
            });

            li.appendChild(checkbox);
            li.appendChild(label);
            checklistContainer.appendChild(li);
        });

        calculateProgress();
    }

    function calculateProgress() {
        const checkboxes = checklistContainer.querySelectorAll('input[type="checkbox"]');
        const total = checkboxes.length;
        let checkedCount = 0;

        checkboxes.forEach((cb) => {
            if (cb.checked) checkedCount++;
        });

        updateProgress(checkedCount, total);
    }

    function updateProgress(checkedCount, total) {
        const percent = total > 0 ? Math.round((checkedCount / total) * 100) : 0;
        progressBarFill.style.width = `${percent}%`;
        progressText.textContent = `${percent}% 완료 (${checkedCount}/${total})`;
    }

    // 7. 전체 복사 버튼 동작
    copyAllBtn.addEventListener("click", async () => {
        if (!currentFullMarkdown) {
            showAlert("복사할 플랜 내용이 없습니다.");
            return;
        }

        try {
            await navigator.clipboard.writeText(currentFullMarkdown);
            const originalText = copyAllBtn.innerHTML;
            copyAllBtn.innerHTML = '<span class="btn-icon">✅</span> 복사 완료!';
            copyAllBtn.style.borderColor = "#10b981";
            copyAllBtn.style.color = "#059669";

            setTimeout(() => {
                copyAllBtn.innerHTML = originalText;
                copyAllBtn.style.borderColor = "";
                copyAllBtn.style.color = "";
            }, 2000);
        } catch (err) {
            console.error("클립보드 복사 실패:", err);
            // 구형 브라우저 폴백
            const tempTextArea = document.createElement("textarea");
            tempTextArea.value = currentFullMarkdown;
            document.body.appendChild(tempTextArea);
            tempTextArea.select();
            document.execCommand("copy");
            document.body.removeChild(tempTextArea);
            alert("전체 마크다운 플랜이 클립보드에 복사되었습니다!");
        }
    });

    // 8. 마크다운(.md) 파일 다운로드 버튼 동작
    downloadMdBtn.addEventListener("click", () => {
        if (!currentFullMarkdown) {
            showAlert("다운로드할 플랜 내용이 없습니다.");
            return;
        }

        const now = new Date();
        const dateStr = now.toISOString().slice(0, 10).replace(/-/g, "");
        const fileName = `AI_학습플랜_${currentGoalName}_${dateStr}.md`;

        const blob = new Blob([currentFullMarkdown], { type: "text/markdown;charset=utf-8" });
        const downloadUrl = URL.createObjectURL(blob);

        const tempLink = document.createElement("a");
        tempLink.href = downloadUrl;
        tempLink.download = fileName;
        document.body.appendChild(tempLink);
        tempLink.click();
        document.body.removeChild(tempLink);
        URL.revokeObjectURL(downloadUrl);
    });
});
