from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from comcast_mock.database import get_session
from comcast_mock.exceptions import not_found
from comcast_mock.models import Category, SubCategory
from comcast_mock.schemas import CategoryOut, SubCategoryOut

router = APIRouter()


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(session: AsyncSession = Depends(get_session)) -> list[CategoryOut]:
    result = await session.execute(select(Category).order_by(Category.id))
    return result.scalars().all()


@router.get(
    "/categories/{category_id}/sub-categories",
    response_model=list[SubCategoryOut],
)
async def list_sub_categories(
    category_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[SubCategoryOut]:
    category = (
        (await session.execute(select(Category).where(Category.id == category_id)))
        .scalars()
        .one_or_none()
    )
    if category is None:
        raise not_found(f"Category {category_id} not found")
    result = await session.execute(
        select(SubCategory).where(SubCategory.category_id == category_id).order_by(SubCategory.id)
    )
    return result.scalars().all()


@router.get("/sub-categories/{sub_category_id}", response_model=SubCategoryOut)
async def get_sub_category(
    sub_category_id: int,
    session: AsyncSession = Depends(get_session),
) -> SubCategoryOut:
    sub = (
        (await session.execute(select(SubCategory).where(SubCategory.id == sub_category_id)))
        .scalars()
        .one_or_none()
    )
    if sub is None:
        raise not_found(f"Sub-category {sub_category_id} not found")
    return sub
