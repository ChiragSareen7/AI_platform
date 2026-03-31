from __future__ import annotations

import os
from dotenv import load_dotenv
import uvicorn

load_dotenv()

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8020"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
