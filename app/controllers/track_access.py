from fastapi import APIRouter, Depends, Request, Query
from pydantic import BaseModel
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

router = APIRouter()

class TrackAccess(BaseModel):
    user_id: str
    file_id: str
    event_type: str  # e.g., "open", "download", "preview"

async def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db

@router.post("/analytics/track-access")
async def track_access(
    event: TrackAccess,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    await db["file_access_logs"].insert_one({
        "user_id": event.user_id,
        "file_id": event.file_id,
        "event_type": event.event_type,
        "timestamp": datetime.utcnow()
    })
    return {"message": "Tracked"}

def convert_objectid(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_objectid(i) for i in obj]
    return obj

@router.get("/analytics/recent-files")
async def get_recent_files(
    user_id: str = Query(...),
    limit: int = Query(5),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$addFields": {"file_obj_id": {"$toObjectId": "$file_id"}}},
        {
            "$group": {
                "_id": "$file_obj_id",
                "lastAccessed": {"$max": "$timestamp"}
            }
        },
        {"$sort": {"lastAccessed": -1}},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "File",  # Make sure the collection name matches exactly (case-sensitive!)
                "localField": "_id",
                "foreignField": "_id",
                "as": "fileDetails"
            }
        },
        {"$unwind": "$fileDetails"},
        {
            "$project": {
                "file": "$fileDetails",
                "lastAccessed": 1
            }
        }
    ]

    results = []
    async for doc in db["file_access_logs"].aggregate(pipeline):
        doc = convert_objectid(doc)
        doc["lastAccessed"] = doc["lastAccessed"].isoformat()
        results.append(doc)

    return results
