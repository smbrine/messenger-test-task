from src.config.settings import get_settings
from src.interface import app
import uvicorn

settings = get_settings()

def main() -> int:
    uvicorn.run("src.main:app", host=settings.api.host, port=settings.api.port, reload=settings.api.debug)
    return 0


if __name__ == "__main__":
    main()