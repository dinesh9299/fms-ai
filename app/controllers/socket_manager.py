# socket_manager.py
from app.controllers.socket_instance import sio

@sio.event
async def connect(sid, environ):
    print(f"🔌 Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"❌ Client disconnected: {sid}")

@sio.event
async def join(sid, user_id):
    await sio.save_session(sid, {"user_id": user_id})
    await sio.enter_room(sid, user_id)
    print(f"✅ User {user_id} joined room")
