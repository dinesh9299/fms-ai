from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Recipient(BaseModel):
    userId: str
    seen: bool = False

class NotificationModel(BaseModel):
    message: str
    parent: str
    time: datetime
    type: str
    by: str
    filetype: Optional[str] = "file"
    recipients: List[Recipient]
