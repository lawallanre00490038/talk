# app/api/deps.py
from typing import Generator

class CommonQueryParams:
    def __init__(self, skip: int = 0, limit: int = 100):
        self.skip = skip
        self.limit = limit

pagination_params = CommonQueryParams