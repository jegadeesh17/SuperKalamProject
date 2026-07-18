# SuperKalam: Loom Video Pitch Strategy & Workflow Guide

This document is designed to help you prepare for your Loom video submission. It contains the core pitch strategy, a step-by-step walkthrough of the app's workflow, and key technical highlights to mention.

---

## 1. The Core Pitch (The "Why")

**The Problem:** UPSC aspirants need constant answer writing practice, but getting human evaluation is expensive, slow, and often biased. 
**The Solution:** SuperKalam is an AI-powered Mock Test Platform that acts as a 24/7 personal mentor. It provides timed mock tests, strictly evaluates answers using UPSC rubrics, and offers encouraging, localized feedback in multiple Indian languages (English, Hindi, Tamil).

## 2. Complete Workflow (What to show in the video)

Follow these steps when recording your screen to demonstrate all functionalities smoothly.

### Step A: The Landing & Mock Test Initiation
1. **Show the Start Screen:** Open `http://127.0.0.1:8000/ui/`. Point out the modern, premium "Glassmorphic" UI.
2. **Action:** Click "Start Now". 
3. **Explain:** Emphasize that the platform acts as a Mock Test environment. It pulls a *random* Previous Year Question (PYQ) from the database to test the student under surprise conditions.

### Step B: The Test Environment
1. **Show the Interface:** Point out the live timer, the assigned question, the year badge, and the word limit.
2. **Action:** Start typing a mock answer in the text area (or paste a pre-written one to save time in the video).
3. **Explain:** Show how the word counter updates dynamically. Mention that the app requires a minimum number of words (20 words) to ensure students are actually writing meaningful answers.

### Step C: Submission & Multilingual Feedback
1. **Action:** Select a feedback language (e.g., Hindi or Tamil) to show off the localization feature, then click "Submit Answer".
2. **Explain:** While the loading spinner is active, explain the **Agentic Pipeline**:
   - The **Retrieval Agent** (ChromaDB) fetches the exact model answer and rubric.
   - The **Evaluator Agent** (Llama-3) strictly scores the answer based on Coverage, Structure, Examples, and Word Limit, enforcing a JSON contract.
   - The **Feedback Agent** translates and formats the feedback into the chosen language as a supportive mentor.

### Step D: The Results & Evaluation
1. **Show the Score:** The UI smoothly animates the overall score (out of 10) and rubric breakdowns.
2. **Show the Feedback:** Scroll down to the Mentor Feedback section. Highlight how the feedback is actionable and encouraging, completely localized into the language you selected.

---

## 3. Key Technical Highlights to Mention

If you have extra time or want to impress the evaluators, drop these keywords during your explanation:
- **RAG (Retrieval-Augmented Generation)**: Mention you use ChromaDB to retrieve the correct model answer and rubric dynamically.
- **Agentic Pipeline**: It’s not just a single prompt. It's a chain of specialized agents (Retrieval -> Evaluator -> Feedback) that handle distinct parts of the logic.
- **Structured LLM Output**: The evaluator agent is forced to output a strict JSON contract, ensuring the frontend always gets parseable score metrics.
- **FastAPI & SQLite**: Mention the clean backend architecture that separates routes, agents, and database operations.

## 4. Practice Checklist
- [ ] Ensure the app is running (`uvicorn app.main:app --reload`).
- [ ] Have a sample answer ready to copy-paste to keep the video concise.
- [ ] Practice speaking while the "Analyzing..." spinner is showing so there's no dead air.
- [ ] Test the language dropdown beforehand to ensure you know what to expect.

Good luck with your Loom submission! You have a great project that solves a real-world problem beautifully.
