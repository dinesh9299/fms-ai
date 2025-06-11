from fastapi import APIRouter, Request, Depends, Query, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List
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
    doc["createdBy"] = str(doc.get("createdBy")) if doc.get("createdBy") else None
    return doc

# ---------------- Controller ----------------
@router.get("/allfiles", response_model=List[dict])
async def get_all_files(
    db: AsyncIOMotorDatabase = Depends(get_db),
    userId: str = Query(...)
):
    try:
        # Get all files from the DB
        all_files_cursor = db.File.find({})
        all_files = [doc async for doc in all_files_cursor]

        visible_files = []

        # -------- Recursive Access Checker --------
        async def has_access_in_folder(folder_id: ObjectId) -> bool:
            children = [f for f in all_files if f.get("parent") and str(f["parent"]) == str(folder_id)]
            for child in children:
                is_public = not child.get("allowedUsers") or len(child["allowedUsers"]) == 0
                is_allowed = userId in [str(uid) for uid in child.get("allowedUsers", [])]
                is_creator = str(child.get("createdBy")) == userId

                if child["type"] == "file" and (is_public or is_allowed or is_creator):
                    return True
                if child["type"] == "folder":
                    access = await has_access_in_folder(child["_id"])
                    if access:
                        return True
            return False

        # -------- Main Filtering Logic --------
        for file in all_files:
            is_public = not file.get("allowedUsers") or len(file["allowedUsers"]) == 0
            is_allowed = userId in [str(uid) for uid in file.get("allowedUsers", [])]
            is_creator = str(file.get("createdBy")) == userId

            if file["type"] == "file":
                if is_public or is_allowed or is_creator:
                    visible_files.append(serialize_file(file))

            elif file["type"] == "folder":
                access = await has_access_in_folder(file["_id"])
                if access or is_creator:
                    visible_files.append(serialize_file(file))

        return jsonable_encoder(visible_files)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"getallfiles error: {str(e)}")
