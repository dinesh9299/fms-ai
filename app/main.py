# main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from app.controllers.socket_instance import sio
from app.controllers import socket_manager  # triggers event binding
from app.controllers import summarize
from app.controllers import search

from app.cors_static import CORSMiddlewareStaticFiles

import socketio

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://192.168.1.11:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
client = AsyncIOMotorClient(MONGO_URI)
db = client.get_default_database()
app.state.db = db

# Mount static folder
app.mount("/uploads", CORSMiddlewareStaticFiles(directory="uploads"), name="uploads")

# Routers
from app.controllers import (
    user_controller, file_controller, get_all_files, getfiles, get_fileby_id,
    decode_controller, file_detail, rename_controller, deletefile_by_id,
    delete_mul_files, download_file, getusers, update_access, filess,
    folder_access, get_notifications,upload_summary,track_access,storage,delete_user,request_access
)

app.include_router(user_controller.router, prefix="/api")
app.include_router(file_controller.router, prefix="/api/files")
app.include_router(get_all_files.router, prefix="/api/files")
app.include_router(getfiles.router, prefix="/api/files")
app.include_router(get_fileby_id.router, prefix="/api/files")
app.include_router(decode_controller.router, prefix="/api")
app.include_router(file_detail.router, prefix="/api/files")
app.include_router(rename_controller.router, prefix="/api/files")
app.include_router(deletefile_by_id.router, prefix="/api/files")
app.include_router(delete_mul_files.router, prefix="/api/files")
app.include_router(download_file.router, prefix="/api/files")
app.include_router(getusers.router, prefix="/api")
app.include_router(update_access.router, prefix="/api/files")
app.include_router(filess.router, prefix="/api/files")
app.include_router(folder_access.router, prefix="/api/files/access")
app.include_router(get_notifications.router, prefix="/api/files")
app.include_router(summarize.router, prefix="/api/files")
app.include_router(search.router, prefix="/api")
app.include_router(upload_summary.router, prefix="/api/files")
app.include_router(track_access.router, prefix="/api/files")
app.include_router(storage.router, prefix="/api/files")
app.include_router(delete_user.router, prefix="/api")
app.include_router(request_access.router, prefix="/api/files")












@app.get("/ping")
async def ping():
    return {"message": "pong"}

# Wrap FastAPI with SocketIO
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
