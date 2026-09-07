from pydantic import BaseModel


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int

