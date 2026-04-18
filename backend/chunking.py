import re

def smart_chunk_text(text, chunk_size=500, overlap=100):
    sentences = re.split(r'(?<=[.!?]) +', text)

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) < chunk_size:
            current_chunk += sentence + " "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + " "

    if current_chunk:
        chunks.append(current_chunk.strip())

    # 🔥 Add overlap
    overlapped_chunks = []
    for i in range(len(chunks)):
        chunk = chunks[i]
        if i > 0:
            chunk = chunks[i-1][-overlap:] + " " + chunk
        overlapped_chunks.append(chunk)

    return overlapped_chunks