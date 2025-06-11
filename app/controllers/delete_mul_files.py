from fastapi import APIRouter, HTTPException, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from bson import ObjectId
from typing import List
import os
import shutil
from urllib.parse import urlparse
from app.controllers.socket_manager import sio  # ✅ now safe to import


router = APIRouter()

# ---------------- DB Dependency ----------------
async def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db

# ---------------- Request Model ----------------
class DeleteMultipleRequest(BaseModel):
    ids: List[str]
    deletedby: str

# ---------------- Helper: Convert URL to file path ----------------
def get_file_path(url_path: str) -> str:
    parsed = urlparse(url_path)
    path = parsed.path.lstrip("/")
    return os.path.join(os.getcwd(), path)

# ---------------- Recursive Delete ----------------
async def delete_recursive(parent_id: ObjectId, db: AsyncIOMotorDatabase):
    children_cursor = db.File.find({"parent": parent_id})
    async for child in children_cursor:
        if child["type"] == "folder":
            await delete_recursive(child["_id"], db)
            folder_path = get_file_path(child["path"])
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path, ignore_errors=True)
                print("Deleted child folder:", folder_path)
        else:
            file_path = get_file_path(child["path"])
            if os.path.exists(file_path):
                os.remove(file_path)
                print("Deleted child file:", file_path)
        await db.File.delete_one({"_id": child["_id"]})

# ---------------- Main Route ----------------
@router.post("/delete-multiple")
async def delete_multiple_items(
    payload: DeleteMultipleRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    request: Request = None
):
    try:
        for id in payload.ids:
            if not ObjectId.is_valid(id):
                continue

            item = await db.File.find_one({"_id": ObjectId(id)})
            if not item:
                continue

            if item["type"] == "folder":
                await delete_recursive(ObjectId(id), db)
                folder_path = get_file_path(item["path"])
                if os.path.exists(folder_path):
                    shutil.rmtree(folder_path, ignore_errors=True)
                    print("Deleted main folder:", folder_path)

            elif item["type"] == "file":
                file_path = get_file_path(item["path"])
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print("Deleted main file:", file_path)

            await db.File.delete_one({"_id": ObjectId(id)})

        # Emit socket event
        io = getattr(request.app.state, "io", None)
        if io:
            await io.emit("storage_updated", payload.deletedby)

        await sio.emit("storage_updated", {"userId": str(payload.deletedby)}, to=str(payload.deletedby))


        return {"message": "Deleted successfully"}

    except Exception as e:
        print("❌ Delete multiple error:", str(e))
        raise HTTPException(status_code=500, detail=f"Delete multiple error: {str(e)}")
