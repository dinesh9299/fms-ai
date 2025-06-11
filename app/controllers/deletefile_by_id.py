from fastapi import APIRouter, HTTPException, Depends, Path, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import os
import shutil
from urllib.parse import urlparse
from app.controllers.socket_manager import sio  # ✅ now safe to import


router = APIRouter()

# Dependency to get DB
async def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db

# --- Helper: Convert full URL path to local file path ---
def get_file_path(url_path: str) -> str:
    # Example: http://127.0.0.1:8000/uploads/myfile.png -> uploads/myfile.png
    parsed = urlparse(url_path)
    path = parsed.path.lstrip("/")  # Remove leading slash
    return os.path.join(os.getcwd(), path)  # Adjust base if needed

# --- Recursive delete function ---
async def delete_recursive(parent_id: ObjectId, db: AsyncIOMotorDatabase):
    children_cursor = db.File.find({"parent": parent_id})
    async for child in children_cursor:
        if child["type"] == "folder":
            await delete_recursive(child["_id"], db)
            folder_path = get_file_path(child["path"])
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path, ignore_errors=True)
        else:
            file_path = get_file_path(child["path"])
            if os.path.exists(file_path):
                os.remove(file_path)

        await db.File.delete_one({"_id": child["_id"]})

# --- Main route ---
@router.delete("/{id}/{deletedby}")
async def delete_item(
    id: str = Path(..., description="MongoDB ID of the file/folder"),
    deletedby: str = Path(..., description="User ID"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    request: Request = None
):
    try:
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="Invalid file ID")

        item = await db.File.find_one({"_id": ObjectId(id)})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        # If folder, recursively delete children
        if item["type"] == "folder":
            await delete_recursive(ObjectId(id), db)
            folder_path = get_file_path(item["path"])
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path, ignore_errors=True)

        elif item["type"] == "file":
            file_path = get_file_path(item["path"])
            if os.path.exists(file_path):
                os.remove(file_path)

        # Delete main item from DB
        await db.File.delete_one({"_id": ObjectId(id)})

        # Emit socket event (optional, if you use socket.io)
        io = getattr(request.app.state, "io", None)
        if io:
            await io.emit("storage_updated", deletedby)
            print("deletedby", deletedby)

        
        await sio.emit("storage_updated", {"userId": str(deletedby)}, to=str(deletedby))


        return {"message": "Deleted successfully"}

    except Exception as e:  
        raise HTTPException(status_code=500, detail=f"Delete error: {str(e)}")
