from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

router = APIRouter()

# Dependency to get DB
async def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db

# Request schema
class RenameRequest(BaseModel):
    id: str
    newName: str

# Helper: serialize ObjectId -> str
def serialize_mongo_doc(doc):
    doc["_id"] = str(doc["_id"])
    if "parent" in doc and doc["parent"]:
        doc["parent"] = str(doc["parent"])
    if "allowedUsers" in doc:
        doc["allowedUsers"] = [str(uid) for uid in doc["allowedUsers"]]
    return doc

@router.post("/rename")
async def rename_file(
    body: RenameRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    try:
        if not ObjectId.is_valid(body.id):
            raise HTTPException(status_code=400, detail="Invalid file ID")

        file = await db.File.find_one({"_id": ObjectId(body.id)})
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        await db.File.update_one(
            {"_id": ObjectId(body.id)},
            {"$set": {"name": body.newName}}
        )

        updated = await db.File.find_one({"_id": ObjectId(body.id)})
        return {"success": True, "file": serialize_mongo_doc(updated)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rename failed: {str(e)}")
