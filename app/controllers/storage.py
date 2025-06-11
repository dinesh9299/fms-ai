from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from bson import ObjectId
from typing import Any
from pymongo.collection import Collection
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import APIRouter, Depends

router = APIRouter()

async def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db



def format_bytes(size: int) -> str:
    """Convert bytes into a human-readable format."""
    for unit in ['Bytes', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

@router.get("/admin-storage/{admin_id}")
async def get_admin_storage(admin_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        admin_object_id = ObjectId(admin_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid admin ID format")

    # Only consider actual files, not folders
    files = await db["File"].find({
        "createdBy": admin_id,
        "type": "file"
    }).to_list(None)

    print("files", files)
    print("id", admin_id)

    total_bytes = sum(int(file.get("size", 0)) for file in files)
    total_mb = round(total_bytes / (1024 * 1024), 2)

    return {
        "adminId": admin_id,
        "totalBytes": total_bytes,
        "totalMB": total_mb,
        "readable": format_bytes(total_bytes)
    }
