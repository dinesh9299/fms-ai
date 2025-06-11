# cors_static.py
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles
from starlette.responses import Response

class CORSMiddlewareStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response: Response = await super().get_response(path, scope)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
