from fastapi import APIRouter, HTTPException, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

router = APIRouter()

async def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db

def serialize_mongo_doc(doc):
    """Safely convert MongoDB document to JSON serializable format."""
    if not doc:
        return doc
    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, list):
            result[key] = [str(v) if isinstance(v, ObjectId) else v for v in value]
        else:
            result[key] = value
    return result

@router.get("/filess/{id}")
async def get_file_and_users(id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid file ID")

    file = await db.File.find_one({"_id": ObjectId(id)})
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    serialized_file = serialize_mongo_doc(file)

    # Convert allowedUsers to ObjectId list
    user_ids = file.get("allowedUsers", [])
    object_ids = [ObjectId(uid) for uid in user_ids if ObjectId.is_valid(uid)]
    print("object_ids:", object_ids)



    # Now query the User collection
    allowed_users = []
    async for user in db.usercredentials.find({"_id": {"$in": object_ids}}):
        allowed_users.append({
            "id": str(user["_id"]),
            "name": user.get("name"),
            "email": user.get("email"),
        })

    serialized_file["allowedUsersDetails"] = allowed_users
    return serialized_file
