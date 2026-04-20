import os
import json
import time
import math
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# -----------------------------------------------------------
# Groq free tier: ~6000 TPM (tokens per minute)
# Safe budget per API call: 4500 tokens input + 800 output
# We reserve 800 tokens for the quiz JSON output
# So input context must stay under ~3700 tokens
# 1 token ≈ 4 chars, so max context chars ≈ 14800
# -----------------------------------------------------------
MAX_CONTEXT_CHARS = 12000   # conservative safe limit
COMPRESS_TO_CHARS = 300     # each chunk compressed to ~300 chars
RATE_LIMIT_PAUSE  = 62      # seconds to wait on 429 error


# ---------------------------
# 🔍 Q&A
# ---------------------------
def generate_answer(query, context_chunks):
    context = "\n\n".join(context_chunks)

    prompt = f"""You are an intelligent document assistant.
Answer the question using ONLY the provided context.

GUIDELINES:
- Do NOT invent or assume information
- Understand meaning, not just exact words
- If partial info exists, answer based on best match
- Only say "Not found in document" if truly nothing relevant exists
- Keep answers clear, structured, and concise

Context:
{context}

Question:
{query}

Answer:"""

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

    prompt = f"""You are a document summarization expert.
Produce a structured summary using EXACTLY these headings:

## Overview
2-3 sentence high-level summary.

## Key Topics
- Bullet list of main subjects/themes

## Main Points
- Bullet list of most important facts or findings

## Conclusion
1-2 sentences on the overall takeaway.

Document Content:
{context}

Summary:"""

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
# 🗜️ CHUNK COMPRESSOR
# Condenses one chunk into a short key-fact summary.
# Called per-chunk so each call is tiny (< 500 tokens).
# ---------------------------
def compress_chunk(chunk_text):
    prompt = f"""Extract the 2-3 most important facts or ideas from this passage.
Write them as compact bullet points. Be concise — max {COMPRESS_TO_CHARS} characters total.
Do not add anything not present in the passage.

Passage:
{chunk_text}

Key facts:"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Extract key facts concisely. Output only bullet points."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=120
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # If compression fails, fall back to first 300 chars of raw chunk
        print(f"⚠️ Compression failed, using raw slice: {e}")
        return chunk_text[:COMPRESS_TO_CHARS]


# ---------------------------
# 📐 TOKEN-SAFE CONTEXT BUILDER
# Samples chunks evenly across the document,
# compresses them only if total chars exceed budget.
# ---------------------------
def build_quiz_context(all_chunks, max_chars=MAX_CONTEXT_CHARS):
    total_chunks = len(all_chunks)

    # Step 1: Evenly sample chunks across the full document
    # so questions cover early, middle AND late sections
    if total_chunks <= 15:
        sampled = all_chunks
    else:
        # Pick indices evenly spread across the doc
        step = total_chunks / 15
        indices = [int(i * step) for i in range(15)]
        sampled = [all_chunks[i] for i in indices]

    raw_context = "\n\n".join(sampled)

    # Step 2: If within budget, use as-is
    if len(raw_context) <= max_chars:
        print(f"✅ Context fits budget: {len(raw_context)} chars, no compression needed")
        return raw_context

    # Step 3: Too big — compress each sampled chunk individually
    print(f"📦 Context too large ({len(raw_context)} chars). Compressing {len(sampled)} chunks...")
    compressed_parts = []

    for i, chunk in enumerate(sampled):
        print(f"  🗜️ Compressing chunk {i+1}/{len(sampled)}...")
        compressed = compress_chunk(chunk)
        compressed_parts.append(compressed)

        # Small pause between compression calls to avoid TPM spikes
        if i < len(sampled) - 1:
            time.sleep(1.5)

    compressed_context = "\n\n".join(compressed_parts)
    print(f"✅ Compressed context: {len(compressed_context)} chars")

    # Step 4: If still over budget (very dense doc), truncate to fit
    if len(compressed_context) > max_chars:
        compressed_context = compressed_context[:max_chars]
        print(f"✂️ Truncated to {max_chars} chars")

    return compressed_context


# ---------------------------
# 🧠 DIFFICULTY PROFILES
# ---------------------------
DIFFICULTY_PROFILES = {
    "easy": {
        "temperature": 0.3,
        "description": """
DIFFICULTY LEVEL: EASY
TARGET: Someone who just skimmed the document for the first time.

QUESTION RULES:
- Ask only about facts that are directly and explicitly stated
- Use simple, clear language — no jargon in the question
- Each question answerable by reading a single sentence

OPTION RULES (CRITICAL):
- Correct answer appears near-verbatim in the document
- Wrong options must be OBVIOUSLY wrong — different topics, opposite ideas, clearly unrelated
- Someone who read once should immediately spot the correct answer
- Do NOT use similar-sounding options

AVOID: Trick questions, subtle distinctions, options that look like each other
""",
    },
    "medium": {
        "temperature": 0.5,
        "description": """
DIFFICULTY LEVEL: MEDIUM
TARGET: Someone who read the document attentively.

QUESTION RULES:
- Ask about specific details, secondary concepts, relationships between ideas
- Mix "what", "which", "how does X relate to Y", "what is the purpose of"
- Some questions require connecting 2 sentences from the document

OPTION RULES:
- Correct answer is in the document but requires careful reading
- Wrong options are topic-related but factually incorrect
- Distractors can be real terms from the document used in wrong context
- Attentive reader gets ~80%; skimmer gets ~50%

AVOID: Too-obvious questions, expert outside knowledge required
""",
    },
    "hard": {
        "temperature": 0.7,
        "description": """
DIFFICULTY LEVEL: HARD
TARGET: Someone who studied the document deeply.

QUESTION RULES:
- Ask about nuanced details, precise distinctions, implicit conclusions
- Require synthesizing multiple parts of the document
- Use "under what condition", "what is the relationship between", "which best explains why"

OPTION RULES (CRITICAL — this is what makes it HARD):
- ALL 4 options must look plausible to a careless reader
- Distractors are close variations, true-but-wrong-context statements, or subtly wrong interpretations
- Options can differ by a single word that changes everything
- Only a careful reader gets these right

AVOID: Obviously wrong options, questions answerable by common sense alone
""",
    }
}


# ---------------------------
# 🧠 QUIZ GENERATOR
# ---------------------------
def generate_quiz(all_chunks, num_questions=5, difficulty="medium"):
    profile = DIFFICULTY_PROFILES.get(difficulty, DIFFICULTY_PROFILES["medium"])

    # Build a token-safe context (compresses large docs automatically)
    context = build_quiz_context(all_chunks)

    prompt = f"""You are an expert quiz designer.

{profile["description"]}

Generate exactly {num_questions} multiple-choice questions based on the document content below.

STRICT OUTPUT FORMAT — ONLY valid JSON, no markdown, no backticks, no extra text:

{{
  "quiz": [
    {{
      "question": "Question text?",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "answer": "A) ...",
      "explanation": "Why correct, and why others are wrong."
    }}
  ]
}}

RULES:
- Base every question on the document content only
- Exactly 4 options per question labeled A), B), C), D)
- "answer" must EXACTLY match one option — copy it character for character
- Do not repeat similar questions
- Rotate which letter holds the correct answer

Document Content:
{context}

JSON Response:"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert quiz designer. Output ONLY valid JSON. No markdown, no code fences, no extra text."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=profile["temperature"],
            max_tokens=2000
        )
        raw = response.choices[0].message.content.strip()

    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "rate_limit" in err_str.lower():
            print(f"⏳ Rate limited on quiz call. Waiting {RATE_LIMIT_PAUSE}s and retrying...")
            time.sleep(RATE_LIMIT_PAUSE)
            # One retry after waiting
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert quiz designer. Output ONLY valid JSON. No markdown, no code fences, no extra text."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=profile["temperature"],
                max_tokens=2000
            )
            raw = response.choices[0].message.content.strip()
        else:
            raise e

    # Strip markdown fences if model adds them
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
        print("Raw output:", raw[:500])
        return []
