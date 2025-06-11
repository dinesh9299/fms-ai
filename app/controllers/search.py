from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from sentence_transformers import SentenceTransformer
from bson import ObjectId
from pydantic import BaseModel, Field  # ✅ Required for BaseModel
from typing import Optional, List      # ✅ Required for type hints
import numpy as np



router = APIRouter()
model = SentenceTransformer('all-MiniLM-L6-v2')  # same model used for file embeddings


from bson import ObjectId
from pydantic_core.core_schema import ValidationInfo

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_validation_schema__(cls, _core_schema, _handler):
        from pydantic import GetCoreSchemaHandler
        from pydantic_core import core_schema
        return core_schema.no_info_after_validator_function(cls.validate, core_schema.str_schema())

    @classmethod
    def validate(cls, value: str, info: ValidationInfo) -> ObjectId:
        if not ObjectId.is_valid(value):
            raise ValueError("Invalid ObjectId")
        return ObjectId(value)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema, handler):
        schema = handler(schema)
        schema.update(type="string")
        return schema


class FileModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    name: str
    type: str
    path: str
    # other fields...
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


def cosine_similarity(vec1, vec2):
    if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

async def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db

@router.post("/search", response_model=List[FileModel])
async def search_files(query: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    if not query.strip():
        raise HTTPException(status_code=400, detail="Empty query")

    query_embedding = model.encode(query)

    files = await db.File.find({"embedding": {"$exists": True}}).to_list(length=1000)

    scored = []
    for f in files:
        file_embedding = np.array(f["embedding"])
        sim = cosine_similarity(query_embedding, file_embedding)
        scored.append((sim, f))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_files = [file for _, file in scored[:10]]

    # Convert each file dict to FileModel for proper serialization
    return [FileModel(**file) for file in top_files]