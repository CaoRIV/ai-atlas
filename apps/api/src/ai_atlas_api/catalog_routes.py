from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from ai_atlas_api.catalog import CatalogError, CatalogRepository
from ai_atlas_api.catalog_models import (
    CatalogQuery,
    CategoriesResponse,
    ErrorResponse,
    Pagination,
    ToolResponse,
    ToolsResponse,
)


def catalog_router(repository: CatalogRepository) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1",
        tags=["catalog"],
        responses={
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )

    def unique_parameters(request: Request) -> None:
        for key in request.query_params:
            if len(request.query_params.getlist(key)) != 1:
                raise CatalogError(
                    422, "VALIDATION_ERROR", "Query parameter không được lặp lại.", key
                )

    def no_parameters(request: Request) -> None:
        if request.query_params:
            raise CatalogError(
                422,
                "VALIDATION_ERROR",
                "Endpoint không nhận query parameters.",
                next(iter(request.query_params)),
            )

    @router.get(
        "/categories",
        response_model=CategoriesResponse,
        dependencies=[Depends(no_parameters)],
    )
    def categories(request: Request) -> CategoriesResponse:
        return CategoriesResponse(data=repository.categories(), request_id=request.state.request_id)

    @router.get(
        "/tools",
        response_model=ToolsResponse,
        dependencies=[Depends(unique_parameters)],
    )
    def tools(request: Request, query: Annotated[CatalogQuery, Query()]) -> ToolsResponse:
        data, total = repository.tools(query)
        return ToolsResponse(
            data=data,
            pagination=Pagination(page=query.page, page_size=query.page_size, total=total),
            request_id=request.state.request_id,
        )

    @router.get(
        "/tools/{tool_id}",
        response_model=ToolResponse,
        responses={404: {"model": ErrorResponse}},
        dependencies=[Depends(no_parameters)],
    )
    def tool(request: Request, tool_id: UUID) -> ToolResponse:
        return ToolResponse(data=repository.tool(tool_id), request_id=request.state.request_id)

    return router
