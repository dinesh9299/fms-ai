from fastapi import APIRouter, HTTPException, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import Optional
from pydantic import BaseModel
from app.controllers.socket_manager import sio  # ✅ now safe to import
from datetime import datetime, timedelta, timezone



router = APIRouter()

async def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db

class AccessUpdateRequest(BaseModel):
    fileId: Optional[str] = None
    folderId: Optional[str] = None
    addUserId: Optional[str] = None
    removeUserId: Optional[str] = None
    by: str


from datetime import datetime

async def save_notification(message, parent_id, filetype, by, user_id, db):
    utc_now = datetime.utcnow().isoformat() + "Z"  # UTC time with 'Z' suffix
    notification = {
        "message": message,
        "parent": str(parent_id),
        "time": utc_now,
        "type": "access",
        "by": by,
        "filetype": filetype,
        "recipients": [{
            "userId": ObjectId(user_id),
            "seen": False
        }]
    }
    await db.Notification.insert_one(notification)




@router.post("/update-access")
async def update_access(data: AccessUpdateRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    if not data.fileId and not data.folderId:
        raise HTTPException(status_code=400, detail="fileId or folderId is required")

    if not data.addUserId and not data.removeUserId:
        raise HTTPException(status_code=400, detail="addUserId or removeUserId is required")

    user_id = data.addUserId or data.removeUserId
    action = "granted" if data.addUserId else "removed"

    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    # ✅ File Access Update
    if data.fileId:
        if not ObjectId.is_valid(data.fileId):
            raise HTTPException(status_code=400, detail="Invalid file ID")

        file = await db.File.find_one({"_id": ObjectId(data.fileId)})
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        update_action = {"$addToSet": {"allowedUsers": ObjectId(user_id)}} if data.addUserId else {"$pull": {"allowedUsers": ObjectId(user_id)}}
        await db.File.update_one({"_id": ObjectId(data.fileId)}, update_action)

        parent_doc = await db.File.find_one({"_id": file.get("parent")})

        parent_name = parent_doc.get("name") if parent_doc else "Unknown"


        # ✅ Save notification
        await save_notification(
            message=f"You were {action} access to file '{file.get('name')}'",
            parent_id = parent_name,
            filetype=file.get("filetype", "file"),
            by=data.by,
            user_id=user_id,
            db=db
        )
        
        await sio.emit("new_notification", {"userId": str(user_id)}, to=str(user_id))


        return {"message": f"Access {action} for file"}

    # ✅ Folder + children access update
    visited = set()

    async def update_all(folder_id: str):
        if folder_id in visited:
            return
        visited.add(folder_id)

        file = await db.File.find_one({"_id": ObjectId(folder_id)})

        parent_doc = await db.File.find_one({"_id": file.get("parent")})

        parent_name = parent_doc.get("name") if parent_doc else "Unknown"


        if file:
            update_action = {"$addToSet": {"allowedUsers": ObjectId(user_id)}} if data.addUserId else {"$pull": {"allowedUsers": ObjectId(user_id)}}
            await db.File.update_one({"_id": ObjectId(folder_id)}, update_action)

            # ✅ Save notification for each file/folder


            await save_notification(
                message=f"You were {action} access to '{file.get('name')}'",
                parent_id = parent_name,
                filetype=file.get("filetype", "folder"),
                by=data.by,
                user_id=user_id,
                db=db
            )

            await sio.emit("notification", {"to": user_id})


        async for child in db.File.find({"parent": ObjectId(folder_id)}):
            await update_all(str(child["_id"]))

    await update_all(data.folderId)
    return {"message": f"Access {action} for folder and children"}





@router.post("/mark-seen/{notification_id}")
async def mark_notification_seen(notification_id: str, request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    body = await request.json()
    user_id = body.get("userId")

    if not ObjectId.is_valid(notification_id) or not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid ID(s)")

    result = await db.Notification.update_one(
        {
            "_id": ObjectId(notification_id),
            "recipients.userId": ObjectId(user_id)
        },
        {
            "$set": {
                "recipients.$.seen": True
            }
        }
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found or already seen")

    return {"message": "Notification marked as seen"}