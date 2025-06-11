from pydantic import BaseModel, Field
from pydantic.json_schema import JsonSchemaValue
from typing import List, Optional, Any
from datetime import datetime
from bson import ObjectId



class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> ObjectId:
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler) -> JsonSchemaValue:
        schema = handler(core_schema)
        schema.update(type="string")
        return schema


class CreateFolderInput(BaseModel):
    name: str
    parentId: Optional[str] = None
    allowedUsers: Optional[List[str]] = []
    createdBy: str
    createdbyName: str


class FileModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    name: str
    type: str  # "file" or "folder"
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
        json_schema_extra = {
            "example": {
                "name": "example.txt",
                "type": "file",
                "path": "uploads/example.txt",
                "filetype": "text/plain",
                "parent": None,
                "size": "12KB",
                "createdtime": "2024-05-10T12:00:00Z",
                "createdBy": "user_id_here",
                "createdbyName": "John Doe",
                "allowedUsers": ["user_id_1", "user_id_2"]
            }
        }
