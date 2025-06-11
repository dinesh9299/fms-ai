from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.user_model import UserInDB  # Assuming your file is named user_model.py
from bson import ObjectId
from typing import List

router = APIRouter()

# ---------------- Dependency ----------------
async def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db

# ---------------- Helper: Convert Mongo _id ----------------
def parse_user(doc):
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    doc.pop("password", None)  # Hide sensitive fields if they exist
    return doc

# ---------------- Get All Users ----------------
@router.get("/getusers", response_model=List[UserInDB])
async def get_users(db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        users_cursor = db.usercredentials.find({})
        users = await users_cursor.to_list(length=None)
        parsed_users = [parse_user(user) for user in users]

        return parsed_users

    except Exception as e:
        print("❌ error:", str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch users")
