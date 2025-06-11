from fastapi import APIRouter, Request, HTTPException, UploadFile, File as UploadFileType, Form
from fastapi.responses import JSONResponse
from bson import ObjectId
from datetime import datetime
import os
from pathlib import Path
import shutil
import json
from typing import List
from typing import List, Optional
from pydantic import BaseModel

from fastapi import Query, Depends

from fastapi import Query, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from fastapi import Body
import numpy as np
from scipy.spatial.distance import cosine
from fastapi.encoders import jsonable_encoder
from keybert import KeyBERT

from datetime import datetime, timedelta, timezone
from app.controllers.socket_manager import sio  # ✅ now safe to import








from fitz import open as pdf_open
from docx import Document


from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')




from app.models.file_model import FileModel, CreateFolderInput, PyObjectId

router = APIRouter()

# Serialize MongoDB documents for JSON

def serialize_document(doc):
    doc["id"] = str(doc["_id"])
    doc["_id"] = str(doc["_id"])
    if doc.get("parent"):
        doc["parent"] = str(doc["parent"])
    if doc.get("allowedUsers"):
        doc["allowedUsers"] = [str(uid) for uid in doc["allowedUsers"]]
    return doc

@router.post("/create-folder", status_code=201)
async def create_folder(data: CreateFolderInput, request: Request):
    folder_path = os.path.join("uploads", data.name)

    existing = await request.app.state.db["File"].find_one({
        "name": data.name,
        "parent": ObjectId(data.parentId) if data.parentId else None,
        "type": "folder"
    })

    if existing:
        return JSONResponse(status_code=400, content={"message": "Folder already exists"})

    IST = timezone(timedelta(hours=5, minutes=30))
    ist_now = datetime.now(IST).isoformat()

    folder_doc = {
        "name": data.name,
        "type": "folder",
        "path": folder_path,
        "parent": ObjectId(data.parentId) if data.parentId else None,
        "allowedUsers": [ObjectId(uid) for uid in data.allowedUsers],
        "createdBy": data.createdBy,
        "createdbyName": data.createdbyName,
        "createdtime": ist_now,  # 🕒 IST time saved properly
    }

    result = await request.app.state.db["File"].insert_one(folder_doc)
    folder_doc["_id"] = result.inserted_id

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(serialize_document(folder_doc))
    )

def extract_text(file_path: str, filetype: str) -> str:
    try:
        # Normalize filetype to handle both short and MIME types
        if filetype in ["application/pdf", "pdf"]:
            with pdf_open(file_path) as doc:
                text = "\n".join(page.get_text() for page in doc)
                if not text.strip():
                    print("[extract_text] No text found, trying OCR fallback...")
                    return extract_text_with_ocr(file_path)
                print(f"[extract_text] Extracted {len(text)} characters from PDF.")
                return text

        elif filetype in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "docx"
        ]:
            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)

        elif filetype.startswith("text/") or filetype == "txt":
            return Path(file_path).read_text()

        else:
            print(f"[extract_text] Unsupported filetype: {filetype}")
            return ""

    except Exception as e:
        print(f"[extract_text] Error: {e}")
        return ""





def generate_embedding(text: str) -> list:
    embedding = model.encode(text)
    return embedding.tolist()





@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = UploadFileType(...),
    name: str = Form(...),
    parentId: str = Form(None),
    filetype: str = Form(...),
    size: str = Form(...),
    createdtime: str = Form(...),
    parentpath: str = Form(None),
    allowedUsers: str = Form("[]"),  # Expecting stringified array
    createdBy: str = Form(...),
    createdbyName: str = Form(...),
    by: str = Form(...)
):
    db = request.app.state.db

    # Save file first
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    saved_path = uploads_dir / file.filename
    with saved_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print("upload directory ", saved_path)

    # Extract text from saved file
    text = extract_text(str(saved_path), filetype)

    kw_model = KeyBERT()
    tags = kw_model.extract_keywords(text, top_n=20)

    print("tags" , tags)



    # Generate embedding (sync call)
    embedding = generate_embedding(text)

    # Parse allowedUsers
    try:
        allowed_user_ids = [ObjectId(uid) for uid in json.loads(allowedUsers)]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid allowedUsers format")

    # Check duplicate file
    existing = await db["File"].find_one({
        "name": name,
        "parent": ObjectId(parentId) if parentId else None,
        "type": "file"
    })
    if existing:
        return {
            "error": f'A file named "{name}" already exists.',
            "success": False
        }

    file_url = f"{request.url.scheme}://{request.client.host}:5000/uploads/{file.filename}"

    doc = {
        "name": name,
        "type": "file",
        "filetype": filetype,
        "path": file_url,
        "parent": ObjectId(parentId) if parentId else None,
        "size": size,
        "createdBy": createdBy,
        "createdbyName": createdbyName,
        "createdtime": datetime.fromisoformat(createdtime),
        "allowedUsers": allowed_user_ids,
        "content": text,
        "embedding": embedding
    }

    result = await db["File"].insert_one(doc)
    saved_doc = await db["File"].find_one({"_id": result.inserted_id})

    await sio.emit("storage_updated", {"userId": str(createdBy)}, to=str(createdBy))

    return {
        "file": serialize_document(saved_doc),
        "success": True
    }



class FileOut(BaseModel):
    _id: str
    name: str
    type: str
    path: Optional[str]
    filetype: Optional[str] = None
    parent: Optional[str] = None
    size: Optional[str] = None
    createdtime: Optional[datetime] = None
    createdBy: str
    createdbyName: str
    allowedUsers: List[str] = []



async def check_folder_access(db: AsyncIOMotorDatabase, folder_id: ObjectId, user_id: str) -> bool:
    children = db.File.find({"parent": folder_id})

    async for child in children:
        is_public = not child.get("allowedUsers") or len(child["allowedUsers"]) == 0
        is_allowed = user_id in [str(uid) for uid in child.get("allowedUsers", [])]

        if is_public or is_allowed:
            return True

        if child["type"] == "folder":
            if await check_folder_access(db, child["_id"], user_id):
                return True

    return False




@router.get("/list", response_model=List[FileOut])
async def get_files(
    db: AsyncIOMotorDatabase = Depends(),  # MongoDB connection
    parent_id: Optional[str] = Query(default=None),
    user_id: str = Query(...)
):
    try:
        # Build query based on parent_id
        query = {"parent": ObjectId(parent_id)} if parent_id else {"parent": None}
        cursor = db.File.find(query)

        visible_files = []

        async for file in cursor:
            # Access rules
            is_public = not file.get("allowedUsers") or len(file["allowedUsers"]) == 0
            is_allowed = user_id in [str(uid) for uid in file.get("allowedUsers", [])]

            if file["type"] == "file":
                if is_public or is_allowed:
                    visible_files.append(file)

            elif file["type"] == "folder":
                if is_public or is_allowed:
                    visible_files.append(file)
                else:
                    if await check_folder_access(db, file["_id"], user_id):
                        visible_files.append(file)

        return jsonable_encoder(visible_files)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.post("/search", response_model=List[dict])
async def search_files(
    request: Request,
    query: str = Body(..., example="resume of dinesh"),
    user_id: str = Body(...),
    top_k: int = Body(5),
    threshold: float = Body(0.4)
):
    db = request.app.state.db

    # Step 1: Lowercase query and generate embedding
    query_lower = query.lower()
    query_embedding = model.encode(query_lower)

    files_cursor = db.File.find({"type": "file"})
    matches = []

    # Step 2: Process each file
    async for file in files_cursor:
        allowed = (
            not file.get("allowedUsers") or
            user_id in [str(uid) for uid in file.get("allowedUsers", [])]
        )
        if not allowed or "embedding" not in file:
            continue

        try:
            sim = 1 - cosine(query_embedding, file["embedding"])
        except Exception as e:
            print(f"[search] Error computing similarity for {file['name']}: {e}")
            continue

        # Step 3: Keyword boost logic
        content_text = file.get("content", "").lower()
        for token in query_lower.split():
            if token in content_text:
                sim += 0.02  # small boost for each keyword match

        # Step 4: Classify confidence
        def get_confidence(score: float) -> str:
            if score >= 0.75:
                return "high"
            elif score >= 0.5:
                return "medium"
            else:
                return "low"

        matches.append({
            "name": file["name"],
            "path": file.get("path"),
            "similarity": float(sim),
            "included": bool(sim >= threshold),
            "confidence": get_confidence(sim)
        })

    # Step 5: Return sorted top-K matches
    matches.sort(key=lambda x: x["similarity"], reverse=True)
    return matches[:top_k]



@router.post("/global-search", response_model=List[dict])
async def global_search_files(
    request: Request,
    query: str = Body(..., example="resume of dinesh"),
    top_k: int = Body(5, description="Number of top results to return"),
    threshold: float = Body(0.4, description="Similarity threshold for including results")
):
    """
    Search all files in the File collection globally, ignoring access restrictions.
    Returns top-K matched files based on query similarity, with optional keyword boost.
    """
    db = request.app.state.db

    # Step 1: Lowercase query and generate embedding
    query_lower = query.lower()
    query_embedding = model.encode(query_lower)

    files_cursor = db.File.find({"type": "file"})
    matches = []

    # Step 2: Process each file
    async for file in files_cursor:
        if "embedding" not in file:
            continue

        try:
            # Calculate cosine similarity (1 - cosine distance)
            sim = 1 - cosine(query_embedding, file["embedding"])
        except Exception as e:
            print(f"[global-search] Error computing similarity for {file['name']}: {e}")
            continue

        # Step 3: Keyword boost logic
        content_text = file.get("content", "").lower()
        for token in query_lower.split():
            if token in content_text:
                sim += 0.02  # Small boost for each keyword match

        # Step 4: Classify confidence
        def get_confidence(score: float) -> str:
            if score >= 0.75:
                return "high"
            elif score >= 0.5:
                return "medium"
            else:
                return "low"

        matches.append({
            "name": file["name"],
            "path": file.get("path"),
            "similarity": float(sim),
            "included": bool(sim >= threshold),
            "confidence": get_confidence(sim),
            "file_id": str(file["_id"]),  # Include file ID for reference
            "filetype": file.get("filetype", ""),  # Include file type
            "createdtime": file.get("createdtime", ""),  # Include creation time
        })

    # Step 5: Return sorted top-K matches
    matches.sort(key=lambda x: x["similarity"], reverse=True)
    return matches[:top_k]