document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const modeBtns = document.querySelectorAll('.mode-btn');
    const evaluationForm = document.getElementById('evaluation-form');
    const answerGroup = document.getElementById('answer-group');
    const answerInput = document.getElementById('answer-input');
    const questionInput = document.getElementById('question-input');
    const languageSelect = document.getElementById('language-select');
    const submitBtn = document.getElementById('submit-btn');
    const wordCountVal = document.getElementById('word-count-val');
    
    // State Containers
    const loadingState = document.getElementById('loading-state');
    const loadingText = document.getElementById('loading-text');
    const errorState = document.getElementById('error-state');
    const errorMsg = document.getElementById('error-msg');
    const resultsContainer = document.getElementById('results-container');
    const evaluateResult = document.getElementById('evaluate-result');
    const modelAnswerResult = document.getElementById('model-answer-result');

    let currentMode = 'evaluate';

    // ─── Event Listeners ───

    // Word Counter
    answerInput.addEventListener('input', () => {
        const text = answerInput.value.trim();
        const words = text ? text.split(/\s+/).length : 0;
        wordCountVal.textContent = words;
        
        // Color code word count
        if (words < 100 || words > 300) {
            wordCountVal.style.color = '#ef4444'; // Red if outside range
        } else {
            wordCountVal.style.color = '#10b981'; // Green if good
        }
    });

    // Mode Toggler
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            modeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            currentMode = btn.dataset.mode;
            
            // Hide results & errors on switch
            hide(resultsContainer);
            hide(errorState);
            
            if (currentMode === 'evaluate') {
                show(answerGroup);
                submitBtn.innerHTML = `<span>Evaluate Answer</span> <i class="fa-solid fa-wand-magic-sparkles"></i>`;
            } else {
                hide(answerGroup);
                submitBtn.innerHTML = `<span>Get Model Answer</span> <i class="fa-solid fa-book-open"></i>`;
            }
        });
    });

    // Form Submit
    evaluationForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const question = questionInput.value.trim();
        const language = languageSelect.value;
        
        if (!question) {
            showError('Please enter a question.');
            return;
        }
        
        hide(errorState);
        hide(resultsContainer);
        show(loadingState);

        if (currentMode === 'evaluate') {
            const answer = answerInput.value.trim();
            if (!answer || answer.split(/\s+/).length < 20) {
                hide(loadingState);
                showError('Please enter a meaningful answer (minimum 20 words).');
                return;
            }
            loadingText.textContent = 'Analyzing your answer against UPSC standards...';
            await handleEvaluate(question, answer, language);
        } else {
            loadingText.textContent = 'Retrieving and translating model answer...';
            await handleModelAnswer(question, language);
        }
    });

    // ─── API Handlers ───

    async function handleEvaluate(question, answer, language) {
        try {
            const res = await fetch('/api/evaluate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question_text: question,
                    answer_text: answer,
                    language: language
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

    async function handleModelAnswer(question, language) {
        try {
            const res = await fetch('/api/model-answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question_text: question,
                    language: language
                })
            });

            const data = await res.json();
            
            if (!res.ok) {
                throw new Error(data.detail || 'Failed to retrieve answer.');
            }

            renderModelAnswerResults(data);
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
        
        // Calculate stroke dasharray (circumference is ~100 based on SVG path)
        // Format: "dash_length, gap_length" -> e.g. 70, 100 for 70%
        const percentage = (score / 10) * 100;
        
        // Reset animation
        circle.setAttribute('stroke-dasharray', `0, 100`);
        circle.className.baseVal = 'circle'; // Reset class
        
        // Set color class
        if (score < 4) circle.classList.add('score-low');
        else if (score < 7) circle.classList.add('score-med');
        else circle.classList.add('score-high');

        // Trigger animation
        setTimeout(() => {
            circle.setAttribute('stroke-dasharray', `${percentage}, 100`);
        }, 100);

        // Rubric Bars
        const rubricContainer = document.getElementById('rubric-bars');
        rubricContainer.innerHTML = '';
        
        for (const [criterion, critScore] of Object.entries(data.scores)) {
            const critPercentage = (critScore / 10) * 100;
            let colorHex = '#10b981'; // Green
            if (critScore < 4) colorHex = '#ef4444'; // Red
            else if (critScore < 7) colorHex = '#f59e0b'; // Yellow

            const niceName = criterion.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

            const html = `
                <div class="rubric-item">
                    <div class="rubric-header">
                        <span>${niceName}</span>
                        <span>${critScore}/10</span>
                    </div>
                    <div class="rubric-bar-bg">
                        <div class="rubric-bar-fill" style="width: 0%; background-color: ${colorHex}"></div>
                    </div>
                </div>
            `;
            rubricContainer.insertAdjacentHTML('beforeend', html);
        }

        // Animate rubric bars
        setTimeout(() => {
            const fills = rubricContainer.querySelectorAll('.rubric-bar-fill');
            const scores = Object.values(data.scores);
            fills.forEach((fill, index) => {
                fill.style.width = `${(scores[index] / 10) * 100}%`;
            });
        }, 100);

        // Feedback
        document.getElementById('mentor-feedback').textContent = data.feedback;

        hide(modelAnswerResult);
        show(evaluateResult);
        show(resultsContainer);
        
        // Scroll to results
        resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function renderModelAnswerResults(data) {
        document.getElementById('ma-topic').textContent = data.topic;
        document.getElementById('ma-year').textContent = `UPSC ${data.year}`;
        document.getElementById('ma-matched-q').textContent = data.matched_question;
        document.getElementById('ma-content').textContent = data.model_answer;
        
        const kpContainer = document.getElementById('ma-key-points');
        kpContainer.innerHTML = '';
        data.key_points.forEach(kp => {
            const li = document.createElement('li');
            li.textContent = kp;
            kpContainer.appendChild(li);
        });

        hide(evaluateResult);
        show(modelAnswerResult);
        show(resultsContainer);

        // Scroll to results
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
