from fastapi import APIRouter, HTTPException, Depends, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.models.file_model import FileModel, PyObjectId

router = APIRouter()

from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
from bson import ObjectId
from pydantic_core.core_schema import ValidationInfo
from pydantic.json_schema import JsonSchemaValue


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any, info: ValidationInfo = None) -> ObjectId:
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler) -> JsonSchemaValue:
        schema = handler(core_schema)
        schema.update(type="string")
        return schema


class FileModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    name: str
    type: str
    path: str
    filetype: Optional[str] = None
    parent: Optional[PyObjectId] = None
    size: Optional[str] = None
    createdtime: Optional[datetime] = None
    createdBy: str
    createdbyName: str
    allowedUsers: List[PyObjectId] = []

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# Dependency to get DB
async def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db
@router.get("/detail", response_model=FileModel)
async def get_file_detail(
    id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    try:
        print("🔍 Received ID:", id)  # Log incoming ID

        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="Invalid file ID")

        file_doc = await db.File.find_one({"_id": ObjectId(id)})
        print("📄 Found Document:", file_doc)  # Log what Mongo returns

        if not file_doc:
            raise HTTPException(status_code=404, detail="File not found")

        return FileModel(**file_doc)

    except Exception as e:
        print("❌ ERROR:", str(e))  # Print actual error to terminal
        raise HTTPException(status_code=500, detail=f"Error fetching file detail: {str(e)}")
