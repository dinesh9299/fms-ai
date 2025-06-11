from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import jwt
import os

router = APIRouter()

@router.get("/decode-token")
async def decode_token(request: Request):
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization token missing")

    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])
        return JSONResponse(content={
            "message": "Token decoded successfully",
            "user": decoded,
        })
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
