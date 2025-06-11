# socket_instance.py
import socketio

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=["http://localhost:5173", "http://192.168.1.11:5173"]
)
