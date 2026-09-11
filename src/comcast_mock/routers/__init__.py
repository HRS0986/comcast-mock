from fastapi import Query


def pagination(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of items to return."),
    offset: int = Query(0, ge=0, description="Number of items to skip."),
) -> tuple[int, int]:
    return limit, offset
