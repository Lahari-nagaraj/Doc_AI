import os
from groq import Groq
from dotenv import load_dotenv

# 🔥 Load environment variables
load_dotenv()

# 🔥 Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_answer(query, context_chunks):
    # 🔥 Combine retrieved chunks
    context = "\n\n".join(context_chunks)

    # 🔥 IMPROVED PROMPT (CRITICAL CHANGE)
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
        model="llama-3.1-8b-instant",  # 🔥 fast + reliable
        messages=[
            {
                "role": "system",
                "content": "You answer strictly based on provided context and reason carefully."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0  # 🔥 keeps answers factual
    )

    return response.choices[0].message.content