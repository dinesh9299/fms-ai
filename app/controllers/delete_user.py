from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

router = APIRouter()

# Dependency to get the DB
async def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db

@router.delete("/deleteuser/{user_id}")
async def delete_user(user_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        user_object_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    result = await db["usercredentials"].delete_one({"_id": user_object_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return JSONResponse(content={"message": "User deleted successfully"})
