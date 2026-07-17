document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const startScreen = document.getElementById('start-screen');
    const startTestBtn = document.getElementById('start-test-btn');
    const testInterface = document.getElementById('test-interface');
    
    const timerDisplay = document.getElementById('timer-display');
    const qYear = document.getElementById('q-year');
    const qWordLimit = document.getElementById('q-word-limit');
    const currentQuestionText = document.getElementById('current-question-text');
    
    const evaluationForm = document.getElementById('evaluation-form');
    const answerInput = document.getElementById('answer-input');
    const languageSelect = document.getElementById('language-select');
    const wordCountVal = document.getElementById('word-count-val');
    
    // State Containers
    const loadingState = document.getElementById('loading-state');
    const loadingText = document.getElementById('loading-text');
    const errorState = document.getElementById('error-state');
    const errorMsg = document.getElementById('error-msg');
    const resultsContainer = document.getElementById('results-container');
    const evaluateResult = document.getElementById('evaluate-result');

    // Timer State
    let timerInterval = null;
    let secondsElapsed = 0;
    let currentQuestion = "";

    // ─── Event Listeners ───

    startTestBtn.addEventListener('click', async () => {
        hide(startScreen);
        show(testInterface);
        await fetchRandomQuestion();
    });

    // Word Counter
    answerInput.addEventListener('input', () => {
        const text = answerInput.value.trim();
        const words = text ? text.split(/\s+/).length : 0;
        wordCountVal.textContent = words;
        
        if (words < 100 || words > 300) {
            wordCountVal.style.color = 'var(--error)';
        } else {
            wordCountVal.style.color = '#10b981';
        }
    });

    // Form Submit
    evaluationForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const answer = answerInput.value.trim();
        const language = languageSelect.value;
        
        if (!answer || answer.split(/\s+/).length < 20) {
            showError('Please enter a meaningful answer (minimum 20 words).');
            return;
        }

        // Stop Timer
        clearInterval(timerInterval);
        
        hide(errorState);
        hide(resultsContainer);
        hide(testInterface);
        show(loadingState);

        await handleEvaluate(currentQuestion, answer, language, secondsElapsed);
    });

    // ─── Timer Logic ───
    function startTimer() {
        secondsElapsed = 0;
        updateTimerDisplay();
        timerInterval = setInterval(() => {
            secondsElapsed++;
            updateTimerDisplay();
        }, 1000);
    }

    function updateTimerDisplay() {
        const m = Math.floor(secondsElapsed / 60).toString().padStart(2, '0');
        const s = (secondsElapsed % 60).toString().padStart(2, '0');
        timerDisplay.textContent = `${m}:${s}`;
    }

    // ─── API Handlers ───

    async function fetchRandomQuestion() {
        try {
            currentQuestionText.textContent = "Loading question...";
            const res = await fetch('/api/random-question');
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.detail || 'Failed to fetch question.');
            
            currentQuestion = data.question_text;
            currentQuestionText.textContent = currentQuestion;
            qYear.textContent = `UPSC ${data.year || 'PYQ'}`;
            qWordLimit.textContent = `${data.word_limit} words`;

            startTimer(); // Start timer once question is loaded
        } catch (err) {
            showError("Could not load a random question. " + err.message);
        }
    }

    async function handleEvaluate(question, answer, language, timeTaken) {
        try {
            const res = await fetch('/api/evaluate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question_text: question,
                    answer_text: answer,
                    language: language,
                    time_taken_seconds: timeTaken
                })
            });

            const data = await res.json();
            
            if (!res.ok) {
                throw new Error(data.detail || 'Evaluation failed.');
            }

            renderEvaluateResults(data);
        } catch (err) {
            showError(err.message);
        } finally {
            hide(loadingState);
        }
    }

    // ─── Renderers ───

    function renderEvaluateResults(data) {
        // Overall Score
        const circle = document.getElementById('overall-circle');
        const valText = document.getElementById('overall-val');
        
        const score = data.overall_score;
        valText.textContent = score.toFixed(1);
        
        const percentage = (score / 10) * 100;
        
        circle.setAttribute('stroke-dasharray', `0, 100`);
        circle.className.baseVal = 'circle';
        
        if (score < 4) circle.style.stroke = 'var(--error)';
        else if (score < 7) circle.style.stroke = '#f59e0b';
        else circle.style.stroke = '#10b981';

        setTimeout(() => {
            circle.setAttribute('stroke-dasharray', `${percentage}, 100`);
        }, 100);

        // Rubric Bars
        const rubricContainer = document.getElementById('rubric-bars');
        rubricContainer.innerHTML = '';
        
        for (const [criterion, critScore] of Object.entries(data.scores)) {
            let colorHex = '#10b981';
            if (critScore < 4) colorHex = 'var(--error)';
            else if (critScore < 7) colorHex = '#f59e0b';

            const niceName = criterion.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

            const html = `
                <div class="rubric-item">
                    <div class="rubric-header">
                        <span>${niceName}</span>
                        <span class="val">${critScore}/10</span>
                    </div>
                    <div class="bar-bg">
                        <div class="bar-fill" style="width: 0%; background-color: ${colorHex}"></div>
                    </div>
                </div>
            `;
            rubricContainer.insertAdjacentHTML('beforeend', html);
        }

        setTimeout(() => {
            const fills = rubricContainer.querySelectorAll('.bar-fill');
            const scores = Object.values(data.scores);
            fills.forEach((fill, index) => {
                fill.style.width = `${(scores[index] / 10) * 100}%`;
            });
        }, 100);

        // Feedback
        document.getElementById('mentor-feedback').textContent = data.feedback;

        show(evaluateResult);
        show(resultsContainer);
        
        resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // ─── Helpers ───
    function show(el) { el.classList.remove('hidden'); }
    function hide(el) { el.classList.add('hidden'); }
    
    function showError(msg) {
        errorMsg.textContent = msg;
        show(errorState);
        hide(loadingState);
    }
});
