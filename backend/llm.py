import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_answer(query, context_chunks):
    context = "\n\n".join(context_chunks)

    prompt = f"""
You are an intelligent document assistant.

Your task is to answer the question using ONLY the provided context.

GUIDELINES:
- Do NOT invent or assume information
- Understand meaning, not just exact words
- If wording differs but meaning matches, still answer
- If partial information is available, answer based on best match
- Only say "Not found in document" if truly no relevant information exists
- Keep answers clear, structured, and concise
- If the answer involves names, lists, or points → format cleanly

Context:
{context}

Question:
{query}

Answer:
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You answer strictly based on provided context and reason carefully."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content


# ---------------------------
# 📝 SUMMARIZER
# ---------------------------
def generate_summary(all_chunks):
    sample_chunks = all_chunks[:30]
    context = "\n\n".join(sample_chunks)

    prompt = f"""
You are a document summarization expert.

Below is the content extracted from a document. Produce a structured, comprehensive summary.

FORMAT YOUR RESPONSE EXACTLY LIKE THIS (use these exact headings):

## Overview
2-3 sentence high-level summary of what this document is about.

## Key Topics
- Bullet list of the main subjects/themes covered

## Main Points
- Bullet list of the most important facts, arguments, or findings

## Conclusion
1-2 sentences on the document's overall takeaway or purpose.

Document Content:
{context}

Summary:
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are an expert summarizer. Follow the format exactly."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=1000
    )

    return response.choices[0].message.content


# ---------------------------
# 🧠 DIFFICULTY PROFILES
# Each profile defines:
#   - temperature: how creative/varied the LLM is
#   - description: the detailed prompt instruction block
# ---------------------------
DIFFICULTY_PROFILES = {
    "easy": {
        "temperature": 0.3,
        "label": "Easy 🟢",
        "description": """
DIFFICULTY LEVEL: EASY
TARGET: Someone who just skimmed the document for the first time.

━━━ QUESTION DESIGN RULES ━━━
- Ask only about facts that are directly and explicitly stated in the document
- Questions should be about the most obvious, central information: main topic, key names, clear definitions
- Use plain, simple language — avoid jargon even if the document uses it
- Each question must be answerable by reading a single sentence in the document
- Do NOT ask about subtle details, numbers, or things requiring inference

━━━ OPTION DESIGN RULES (CRITICAL) ━━━
- The correct answer must appear word-for-word or near-verbatim in the document
- The 3 wrong options must be OBVIOUSLY wrong — not sneakily wrong
- Wrong options should be: completely different topics, opposite ideas, or things clearly unrelated to the question
- Someone who read the document once should immediately recognize the correct answer
- DO NOT use options that are close variations of each other — keep them clearly distinct

━━━ WHAT TO AVOID ━━━
❌ Similar-sounding options (e.g., Adam / AdaMax / AdaGrad / RMSProp for a beginner)
❌ Technical distinctions that require deep knowledge
❌ Questions where 2 options could both seem correct
❌ Trick questions or double negatives

━━━ GOOD EASY EXAMPLE ━━━
Q: What is this document mainly about?
A) Baking bread  B) Machine learning algorithms  C) Ancient Roman history  D) Ocean biology
✅ Obvious correct answer, clearly wrong distractors
""",
    },

    "medium": {
        "temperature": 0.5,
        "label": "Medium 🟡",
        "description": """
DIFFICULTY LEVEL: MEDIUM
TARGET: Someone who read the document attentively and understood the main ideas.

━━━ QUESTION DESIGN RULES ━━━
- Ask about specific supporting details, secondary concepts, and relationships between ideas
- Questions should require the user to recall specific information — not just the main theme
- Some questions can require connecting 2 sentences from different parts of the document
- Mix question types: "what", "which", "how does X relate to Y", "what is the purpose of"
- Avoid questions answerable by pure guessing or common sense alone

━━━ OPTION DESIGN RULES ━━━
- The correct answer is clearly in the document but requires careful reading to find
- Wrong options should be plausible and topic-related — not obviously absurd
- Distractors can be: real terms from the document used in wrong context, partially correct statements, or common misconceptions about the topic
- An attentive reader gets 75-85% right; a skimmer gets ~50%

━━━ WHAT TO AVOID ━━━
❌ Questions that are too obvious (main topic, clearly stated single facts)
❌ Questions requiring expert outside knowledge
❌ Options that are completely unrelated to the document's domain

━━━ GOOD MEDIUM EXAMPLE ━━━
Q: What problem does the proposed approach primarily address?
A) High inference latency  B) Overfitting on small datasets  C) GPU memory constraints  D) Label noise in annotations
✅ All options are plausible problems in the domain — only one matches the document
""",
    },

    "hard": {
        "temperature": 0.7,
        "label": "Hard 🔴",
        "description": """
DIFFICULTY LEVEL: HARD
TARGET: Someone who studied the document thoroughly and wants to be genuinely challenged.

━━━ QUESTION DESIGN RULES ━━━
- Ask about nuanced details, precise technical distinctions, edge cases, or implicit conclusions
- Questions should require synthesizing information from multiple parts of the document
- Use reasoning-based questions: "under what condition", "what is the relationship between X and Y", "which of the following best explains why"
- Can ask about specific numbers, exact definitions, or subtle differences between similar concepts
- The correct answer may require combining 2+ pieces of information or drawing a logical conclusion

━━━ OPTION DESIGN RULES (CRITICAL — this is what makes it HARD) ━━━
- ALL 4 options must look plausible to someone who didn't read carefully
- Distractors must be: close variations of the correct answer, true statements that don't answer THIS specific question, or subtly wrong interpretations of real document content
- Options can differ by a single critical word that changes everything
- A skimmer should get these wrong; only a careful reader gets them right
- NEVER use obviously wrong or off-topic distractors on hard questions
- Each distractor should be something a reasonable person might genuinely believe is correct

━━━ WHAT TO AVOID ━━━
❌ Obviously wrong options (like unrelated topics)
❌ Questions answerable without reading the document
❌ Questions with 2+ options that are clearly identical in meaning

━━━ GOOD HARD EXAMPLE ━━━
Q: Under what specific condition does the model fail to generalize according to the document?
A) When trained on datasets larger than 10,000 samples
B) When input features are not normalized prior to training
C) When the learning rate exceeds 0.01 during the fine-tuning phase
D) When dropout regularization is applied after the final classification layer
✅ All 4 are technically plausible and domain-relevant — only one matches the document exactly
""",
    }
}


# ---------------------------
# 🧠 QUIZ GENERATOR
# ---------------------------
def generate_quiz(all_chunks, num_questions=5, difficulty="medium"):
    sample_chunks = all_chunks[:25]
    context = "\n\n".join(sample_chunks)

    profile = DIFFICULTY_PROFILES.get(difficulty, DIFFICULTY_PROFILES["medium"])
    difficulty_instructions = profile["description"]
    temperature = profile["temperature"]

    prompt = f"""
You are an expert quiz designer specializing in adaptive difficulty assessment.

{difficulty_instructions}

Based on the document content below, generate exactly {num_questions} multiple-choice questions.

STRICT OUTPUT FORMAT — respond with ONLY valid JSON, no extra text, no markdown, no backticks:

{{
  "quiz": [
    {{
      "question": "Question text here?",
      "options": ["A) Option one", "B) Option two", "C) Option three", "D) Option four"],
      "answer": "A) Option one",
      "explanation": "Explain why this is correct AND briefly why each wrong option is incorrect."
    }}
  ]
}}

UNIVERSAL RULES (apply to ALL difficulty levels):
- Every question must be 100% grounded in the document content — no outside knowledge
- Each question must have exactly 4 options labeled A), B), C), D)
- The "answer" field must EXACTLY match one of the 4 options — copy it character for character
- Do NOT repeat similar questions — vary the topics covered
- Rotate which letter holds the correct answer — don't always put it in position A)
- Write explanations that help the user learn, not just confirm the answer

Document Content:
{context}

JSON Response:
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": "You are an expert adaptive quiz designer. You output ONLY valid JSON. Absolutely no markdown, no code fences, no extra text before or after the JSON object."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=2500
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if model adds them anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        parsed = json.loads(raw)
        return parsed.get("quiz", [])
    except json.JSONDecodeError as e:
        print("❌ JSON parse error:", e)
        print("Raw output:", raw)
        return []
