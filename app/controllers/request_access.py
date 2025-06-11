from fastapi import APIRouter, HTTPException, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pydantic import BaseModel
from app.controllers.socket_manager import sio
from datetime import datetime

router = APIRouter()

async def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db

class AccessRequest(BaseModel):
    fileId: str
    userId: str
    requestedBy: str

async def save_notification(message, parent_id, filetype, by, recipient_id, db):
    utc_now = datetime.utcnow().isoformat() + "Z"
    notification = {
        "message": message,
        "parent": str(parent_id),
        "time": utc_now,
        "type": "access_request",
        "by": by,
        "filetype": filetype,
        "recipients": [{
            "userId": ObjectId(recipient_id),
            "seen": False
        }]
    }
    await db.Notification.insert_one(notification)

@router.post("/request-access")
async def request_access(data: AccessRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    # Validate IDs
    if not ObjectId.is_valid(data.fileId):
        raise HTTPException(status_code=400, detail="Invalid file ID")
    if not ObjectId.is_valid(data.userId):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    # Find the file
    file = await db.File.find_one({"_id": ObjectId(data.fileId)})
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Get file admin/owner (assuming 'owner' field exists in File document)
    admin_id = file.get("createdBy")
    if not admin_id:
        raise HTTPException(status_code=400, detail="File has no admin/owner")
    if not ObjectId.is_valid(admin_id):
        raise HTTPException(status_code=400, detail="Invalid admin ID")

    # Get parent document for parent name
    parent_doc = await db.File.find_one({"_id": file.get("parent")})
    parent_name = parent_doc.get("name") if parent_doc else "Unknown"

    # Save notification for admin
    await save_notification(
        message=f"User {data.requestedBy} requested access to '{file.get('name')}'",
        parent_id=parent_name,
        filetype=data.userId,
        by=data.fileId,
        recipient_id=str(admin_id),
        db=db,
    )

    # Emit real-time notification to admin
    await sio.emit("new_notification", {"userId": str(admin_id)}, to=str(admin_id))

    return {"message": "Access request sent to file admin"}



class UpdateNotificationRequest(BaseModel):
    notificationId: str

@router.put("/accept-access")
async def accept_access(
    data: UpdateNotificationRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if not ObjectId.is_valid(data.notificationId):
        raise HTTPException(status_code=400, detail="Invalid notification ID")

    notification_obj_id = ObjectId(data.notificationId)

    # Check if notification exists and is of type 'access_request'
    notification = await db.Notification.find_one({"_id": notification_obj_id})
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.get("type") != "access_request":
        raise HTTPException(status_code=400, detail="Notification is not an access request")

    # Update the type to 'accepted'
    result = await db.Notification.update_one(
        {"_id": notification_obj_id},
        {"$set": {"type": "accepted"}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update notification")

    return {"message": "Access request accepted"}

