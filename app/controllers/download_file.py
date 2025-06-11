from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import FileResponse
import os

router = APIRouter()

# ----------------- File Download Route -----------------
@router.get("/download/{filename}/{name}")
async def download_file(
    filename: str = Path(..., description="Actual filename on disk"),
    name: str = Path(..., description="Filename to show for download"),
):
    # Construct full path to the file
    file_path = os.path.join(os.getcwd(), "uploads", filename)

    # Check if file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        return FileResponse(
            path=file_path,
            filename=name,
            media_type='application/octet-stream',
        )
    except Exception as e:
        print("Download failed:", str(e))
        raise HTTPException(status_code=500, detail="Failed to download file.")
