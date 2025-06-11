from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import pdfplumber
import docx
from transformers import pipeline
from fastapi import Request
from bson import ObjectId


from openai import OpenAI

# openai.api_key = "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"

client = OpenAI(api_key="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")  # Set up your API key



router = APIRouter()
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

def clean_and_chunk_text(text, max_chunk=800):
    import re
    text = re.sub(r'\s+', ' ', text).strip()
    words = text.split()
    chunks = [" ".join(words[i:i + max_chunk]) for i in range(0, len(words), max_chunk)]
    return chunks

@router.post("/summarize")
async def summarize_file(file: UploadFile = File(...)):
    try:
        text = ""

        # Ensure the file is read from the beginning
        filename = file.filename.lower()
        print("Received file:", filename)

        if file.filename.endswith(".pdf") or file.content_type == "application/pdf":
            import io
            file_bytes = await file.read()
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        elif file.filename.endswith(".docx") or file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            import io
            file_bytes = await file.read()
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join(p.text for p in doc.paragraphs)

        elif file.filename.endswith(".txt") or file.content_type == "text/plain":
            file_bytes = await file.read()
            text = file_bytes.decode("utf-8")

        else:
            raise ValueError("Unsupported file type")

        print("Text length extracted:", len(text))

        if not text.strip():
            return {"summary": "❌ File is empty or unreadable."}

        result = summarizer(text[:1000], max_length=150, min_length=40, do_sample=False)
        return {"summary": result[0]['summary_text']}

    except Exception as e:
        print("❌ Summarization failed:", e)
        raise HTTPException(status_code=500, detail="Summarization failed")



@router.post("/open-summarize/{file_id}")
async def summarize_file(file_id: str, request: Request):
    db = request.app.state.db
    file = await db["File"].find_one({"_id": ObjectId(file_id)})


    if not file or "content" not in file:
        raise HTTPException(status_code=404, detail="File not found or no content")

    content = file["content"]
    prompt = f"Please summarize the following document in bullet points:\n\n{content[:3000]}"  # truncate for safety

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # or any model from OpenRouter
        messages=[
            {"role": "system", "content": "You are a helpful summarization assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    summary = response.choices[0].message["content"]
    return {"summary": summary}
