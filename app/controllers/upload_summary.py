from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import pdfplumber
import docx
from transformers import pipeline

router = APIRouter()
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

def clean_and_chunk_text(text, max_chunk=800):
    import re
    text = re.sub(r'\s+', ' ', text).strip()
    words = text.split()
    chunks = [" ".join(words[i:i + max_chunk]) for i in range(0, len(words), max_chunk)]
    return chunks

@router.post("/upload-summarize")
async def summarize_file(file: UploadFile = File(...)):
    try:
        # Step 1: Extract all text
        text = ""
        if file.filename.endswith(".pdf"):
            with pdfplumber.open(file.file) as pdf:
                text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        elif file.filename.endswith(".docx"):
            doc = docx.Document(file.file)
            text = "\n".join(p.text for p in doc.paragraphs)
        elif file.filename.endswith(".txt"):
            text_bytes = await file.read()
            text = text_bytes.decode("utf-8")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        if not text.strip():
            return JSONResponse(content={"summary": "❌ File is empty or contains no readable text."})

        # Step 2: Chunk large text for summarization
        chunks = clean_and_chunk_text(text)
        summaries = []

        for chunk in chunks:
            result = summarizer(chunk, max_length=150, min_length=40, do_sample=False)
            summaries.append(result[0]['summary_text'])

        # Step 3: Combine into a final summary
        combined_summary = " ".join(summaries)

        return {"summary": combined_summary}

    except Exception as e:
        print("[Summarize Error]:", e)
        raise HTTPException(status_code=500, detail="Summarization failed")
