from collections.abc import Sequence

from app.models.category import Category
from app.models.subcategory import Subcategory
from app.repositories.category import CategoryRepository
from app.repositories.subcategory import SubcategoryRepository


class InvalidCategoriesError(Exception):
    """Raised when some of the supplied category IDs do not exist."""


class InvalidSubcategoriesError(Exception):
    """Raised when some of the supplied subcategory IDs do not exist."""


async def fetch_categories(
    repository: CategoryRepository, ids: Sequence[int]
) -> list[Category]:
    unique_ids = list(dict.fromkeys(ids))
    categories = await repository.list_by_ids(unique_ids)
    if len(categories) != len(unique_ids):
        raise InvalidCategoriesError(
            "One or more categories do not exist or are deleted."
        )
    return categories


async def fetch_subcategories(
    repository: SubcategoryRepository, ids: Sequence[int]
) -> list[Subcategory]:
    unique_ids = list(dict.fromkeys(ids))
    subcategories = await repository.list_by_ids(unique_ids)
    if len(subcategories) != len(unique_ids):
        raise InvalidSubcategoriesError(
            "One or more subcategories do not exist or are deleted."
        )
    return subcategories
