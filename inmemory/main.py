"""
In-Memory OpenQueue - Main Entry Point
"""

import os
import uvicorn
from server import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)