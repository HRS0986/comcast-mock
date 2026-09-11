import uvicorn

from comcast_mock.config import settings


def main() -> None:
    uvicorn.run(
        "comcast_mock.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info",
    )


if __name__ == "__main__":
    main()
