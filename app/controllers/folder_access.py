from fastapi import APIRouter, HTTPException, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Set

router = APIRouter()

async def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db

@router.get("/all-users/{folder_id}")
async def get_users_with_access_to_all_files(folder_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    if not ObjectId.is_valid(folder_id):
        raise HTTPException(status_code=400, detail="Invalid folder ID")

    visited: Set[str] = set()
    all_files: List[dict] = []

    async def collect_all_files(file_id: str):
        if file_id in visited:
            return
        visited.add(file_id)

        node = await db.File.find_one({"_id": ObjectId(file_id)})
        if not node:
            return
        all_files.append(node)

        async for child in db.File.find({"parent": ObjectId(file_id)}):
            await collect_all_files(str(child["_id"]))

    await collect_all_files(folder_id)

    if not all_files:
        return {"count": 0, "users": []}

    # Build list of sets of allowedUsers
    user_sets = []
    for file in all_files:
        ids = file.get("allowedUsers", [])
        user_set = set(str(uid) for uid in ids)
        user_sets.append(user_set)

    # Intersect all sets
    common_user_ids = set(user_sets[0])
    for user_set in user_sets[1:]:
        common_user_ids.intersection_update(user_set)

    if not common_user_ids:
        return {"count": 0, "users": []}

    # Fetch user details
    object_ids = [ObjectId(uid) for uid in common_user_ids if ObjectId.is_valid(uid)]
    cursor = db.usercredentials.find({"_id": {"$in": object_ids}}, {"name": 1, "email": 1})
    users = []
    async for user in cursor:
        users.append({
            "id": str(user["_id"]),
            "name": user.get("name"),
            "email": user.get("email"),
        })

    return {
        "count": len(users),
        "users": users
    }
