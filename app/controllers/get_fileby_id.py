from fastapi import APIRouter, HTTPException, Request, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

# ------------------ Dependency ------------------
async def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db

# ------------------ Pydantic Response Model ------------------
class FileOut(BaseModel):
    _id: str
    name: str
    type: str
    path: Optional[str] = None
    parent: Optional[str] = None
    size: Optional[str] = None
    createdBy: str
    createdbyName: str
    allowedUsers: list

# ------------------ Serializer ------------------
def serialize_file(doc):
    doc["_id"] = str(doc["_id"])
    if "parent" in doc:
        doc["parent"] = str(doc["parent"]) if doc["parent"] else None
    doc["allowedUsers"] = [str(uid) for uid in doc.get("allowedUsers", [])]
    return doc

# ------------------ Route ------------------
@router.get("/getfilebyid/{id}", response_model=FileOut)
async def get_file_by_id(id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        # ✅ Validate ID format
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="Invalid ObjectId format")

        # ✅ Try finding the document
        file = await db.File.find_one({"_id": ObjectId(id)})
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        return serialize_file(file)

    except Exception as e:
        print("Error in /getfilebyid:", e)  # ✅ Log to console
        raise HTTPException(status_code=500, detail=f"Error fetching file: {str(e)}")