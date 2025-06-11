import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use $PORT from Render
    uvicorn.run("app.main:socket_app", host="0.0.0.0", port=port)
