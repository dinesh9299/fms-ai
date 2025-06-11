from fastapi import APIRouter, HTTPException, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List
from datetime import datetime

router = APIRouter()

async def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db

@router.get("/notification/{user_id}")
async def get_notifications_for_user(user_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    try:
        cursor = db.Notification.find({"recipients.userId": ObjectId(user_id)}).sort("time", -1)
        notifications = []
        async for doc in cursor:
            # Find the recipient's entry for this user
            recipient = next((r for r in doc.get("recipients", []) if str(r["userId"]) == user_id), None)
            notifications.append({
                "_id": str(doc["_id"]),
                "message": doc.get("message"),
                "parent": doc.get("parent"),
                "time": doc.get("time"),
                "type": doc.get("type"),
                "by": doc.get("by"),
                "seen": recipient.get("seen", False) if recipient else False,
                "filetype": doc.get("filetype", "file")
            })

        return notifications

    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")
