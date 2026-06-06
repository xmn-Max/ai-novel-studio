<<<<<<< HEAD
import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
=======
import os
from pathlib import Path
import uvicorn

# 加载 .env 文件
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
