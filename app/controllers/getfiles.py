from fastapi import APIRouter, Request, Depends, Query, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Optional
from fastapi.encoders import jsonable_encoder

router = APIRouter()

# ---------------- Dependency ----------------
async def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db

# ---------------- Serializer ----------------
def serialize_file(doc):
    doc["_id"] = str(doc["_id"])
    doc["parent"] = str(doc["parent"]) if doc.get("parent") else None
    doc["allowedUsers"] = [str(uid) for uid in doc.get("allowedUsers", [])]
    return doc

# ---------------- Recursive Access Checker ----------------
async def check_folder_access(folder_id: ObjectId, user_id: str, db: AsyncIOMotorDatabase) -> bool:
    children_cursor = db.File.find({ "parent": folder_id })
    async for child in children_cursor:
        is_public = not child.get("allowedUsers") or len(child["allowedUsers"]) == 0
        is_allowed = user_id in [str(uid) for uid in child.get("allowedUsers", [])]

        if child["type"] == "file" and (is_public or is_allowed):
            return True
        elif child["type"] == "folder":
            if is_public or is_allowed:
                return True
            if await check_folder_access(child["_id"], user_id, db):
                return True
    return False

# ---------------- Main Route ----------------
@router.get("/getfiles", response_model=List[dict])
async def get_files(
    db: AsyncIOMotorDatabase = Depends(get_db),
    parentId: Optional[str] = Query(default=None),  # ✅ param name corrected
    userId: str = Query(...)  # ✅ param name corrected
):
    try:
        query = { "parent": ObjectId(parentId) } if parentId else { "parent": None }
        cursor = db.File.find(query)
        visible_files = []

        async for file in cursor:
            is_public = not file.get("allowedUsers") or len(file["allowedUsers"]) == 0
            is_allowed = userId in [str(uid) for uid in file.get("allowedUsers", [])]

            if file["type"] == "file":
                if is_public or is_allowed:
                    visible_files.append(serialize_file(file))
            elif file["type"] == "folder":
                if is_public or is_allowed:
                    visible_files.append(serialize_file(file))
                else:
                    has_access = await check_folder_access(file["_id"], userId, db)
                    if has_access:
                        visible_files.append(serialize_file(file))

        return jsonable_encoder(visible_files)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"getFiles error: {str(e)}")



@router.get("/getallfiles", response_model=List[dict])
async def get_all_files(
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        query = {"type": "file"}
   

        cursor = db.File.find(query)
        files = [serialize_file(file) async for file in cursor]

        return jsonable_encoder(files)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"getAllFiles error: {str(e)}")