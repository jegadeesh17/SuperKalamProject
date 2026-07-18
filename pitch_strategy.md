# SuperKalam: Loom Video Pitch Script

## 1. Problem Statement

"Hi everyone, I'm Jegadeesh, and today I'm presenting SuperKalam. During my research into UPSC preparation, I noticed a glaring problem: aspirants desperately need daily answer writing practice to succeed in the Mains exam, but getting consistent, high-quality human evaluation is incredibly expensive, slow, and often biased. I built SuperKalam to solve this. It's an AI-powered Mock Test Platform that acts as a 24/7 personal mentor. It provides timed mock tests, strictly evaluates answers using official UPSC rubrics, and most importantly, offers encouraging, localized feedback in English, Hindi, and Tamil."

## 2. UI Showcase & Explanation

"Let's dive into the platform. When you land on SuperKalam, you'll immediately notice the modern, 'Glassmorphic' UI I designed. I wanted the interface to feel premium and distraction-free so students can focus entirely on the exam. 

When I click 'Start Now', the platform doesn't just ask me to paste a question—it generates a true mock test environment by pulling a random Previous Year Question from the database. 

Here in the test interface, you can see the live timer to simulate real exam pressure, the assigned question with its year and word limit, and a dynamic word counter. The platform forces a minimum word count so students can't game the system with one-liners. 

Once I've written my answer, I can select my preferred language—let's say Hindi—and hit 'Submit'."

## 3. Deep Explanation of the Tech Stack & Why It Was Chosen

"While the answer is being analyzed, let me explain the tech stack powering this under the hood. 

For the **Backend**, I chose **FastAPI** because of its incredible speed, async capabilities, and clean routing structure. This allows my API to handle long-running LLM inferences without blocking the server.

For the **Database layer**, I'm actually using two systems: 
1. **SQLite with SQLAlchemy** handles structured data like topics, rubrics, and the student's attempt history. It's lightweight and perfect for this scale.
2. **ChromaDB**, a vector database, is used for our **RAG (Retrieval-Augmented Generation)** architecture. I chose ChromaDB because it runs locally and allows the system to embed any question and instantly find the closest matching PYQ and its official model answer.

For the **LLM**, I integrated the **OpenRouter API** using `meta-llama/llama-3.1-8b-instruct`. I chose this specific Llama-3 model because it's highly capable of adhering to strict system prompts, which is crucial for the complex agentic pipeline I built."

## 4. Run-Through of the Stack (The Agentic Pipeline)

"What makes SuperKalam powerful is that it isn't just a simple wrapper around a single LLM prompt. It uses an **Agentic Pipeline**—a chain of specialized AI agents working together:

1. **The Retrieval Agent:** First, this agent uses ChromaDB to fetch the exact model answer and the official UPSC rubric for the assigned topic.
2. **The Evaluator Agent:** Next, this agent takes the student's answer, the model answer, and the rubric. I've designed it to strictly score the answer across four dimensions—Coverage, Structure, Examples, and Word Limit. Crucially, I enforce a strict JSON output contract so the frontend receives reliable, parseable numbers every time.
3. **The Feedback Agent:** Finally, this agent takes the raw evaluator notes and translates them into a supportive, mentor-like tone in the student's chosen language.

And here are the results on the UI! As you can see, the overall score animates beautifully, we get a detailed rubric breakdown, and down here, we have actionable, encouraging mentor feedback completely localized into Hindi. 

Thank you for watching, and I'm excited to hear your feedback on SuperKalam!"
