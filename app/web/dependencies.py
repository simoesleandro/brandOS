import os
from functools import lru_cache

from app.core.brandos_service import BrandOSService


def get_project_base_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@lru_cache(maxsize=1)
def get_brandos_service() -> BrandOSService:
    return BrandOSService(get_project_base_dir())
