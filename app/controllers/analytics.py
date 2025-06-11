from fastapi import Query
from bson import ObjectId

@router.get("/analytics/recent-files")
async def get_recent_files(
    user_id: str = Query(...),
    limit: int = Query(5),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    pipeline = [
        {"$match": {"user_id": user_id}},
        {
            "$group": {
                "_id": "$file_id",
                "lastAccessed": {"$max": "$timestamp"}
            }
        },
        {"$sort": {"lastAccessed": -1}},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "files",  # your actual files collection
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
        doc["file"]["_id"] = str(doc["file"]["_id"])
        doc["lastAccessed"] = doc["lastAccessed"].isoformat()
        results.append(doc)

    return results
