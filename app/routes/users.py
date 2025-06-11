from fastapi import APIRouter, HTTPException, Request, Depends
from models.user_model import UserCreate, UserBase
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from bson import ObjectId
import os
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage

load_dotenv()

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET", "yoursecretkey")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")


def create_jwt(user_id: str, role: str):
    payload = {
        "id": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


@router.post("/login")
async def login(request: Request, email: str, password: str):
    db = request.app.state.db
    user = await db.usercredentials.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not pwd_context.verify(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_jwt(str(user["_id"]), user["role"])
    return {"token": token, "role": user["role"]}


@router.post("/create-first-admin")
async def create_first_admin(request: Request, name: str, email: str, password: str):
    db = request.app.state.db
    existing = await db.usercredentials.find_one({"role": "admin"})
    if existing:
        raise HTTPException(status_code=400, detail="Admin already exists")

    hashed = pwd_context.hash(password)
    result = await db.usercredentials.insert_one({
        "name": name,
        "email": email,
        "password": hashed,
        "role": "admin",
        "department": "N/A",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })

    return {"id": str(result.inserted_id), "message": "Admin created"}


@router.post("/register")
async def register_user(request: Request, user: UserCreate):
    db = request.app.state.db
    existing = await db.usercredentials.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed = pwd_context.hash(user.password)
    user_data = user.dict()
    user_data["password"] = hashed
    user_data["created_at"] = datetime.utcnow()
    user_data["updated_at"] = datetime.utcnow()

    await db.usercredentials.insert_one(user_data)

    # Email
    msg = EmailMessage()
    msg["Subject"] = "Welcome! Your Account Has Been Created"
    msg["From"] = EMAIL_USER
    msg["To"] = user.email
    msg.set_content(f"Hi {user.name},\n\nYour login password is: {user.password}")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
    except Exception as e:
        print("Email failed:", e)

    return {"message": "User created and email sent"}


@router.get("/users")
async def get_users(request: Request):
    db = request.app.state.db
    users = await db.usercredentials.find().to_list(1000)
    for u in users:
        u["id"] = str(u["_id"])
        del u["_id"]
        del u["password"]
    return {"message": "users list", "data": users}


@router.delete("/user/{id}")
async def delete_user(id: str, request: Request):
    db = request.app.state.db
    await db.usercredentials.delete_one({"_id": ObjectId(id)})
    return {"message": "User deleted successfully"}


@router.post("/change-password")
async def change_password(request: Request, currentPassword: str, newPassword: str):
    db = request.app.state.db
    user_id = request.headers.get("user-id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user = await db.usercredentials.find_one({"_id": ObjectId(user_id)})
    if not user or not pwd_context.verify(currentPassword, user["password"]):
        raise HTTPException(status_code=403, detail="Current password incorrect")

    hashed = pwd_context.hash(newPassword)
    await db.usercredentials.update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"password": hashed}}
    )
    return {"message": "Password updated successfully"}
