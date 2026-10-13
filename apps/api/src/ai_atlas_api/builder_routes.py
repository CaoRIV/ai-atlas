from fastapi import APIRouter, Depends, Request

from ai_atlas_api.builder import BuilderLiteService
from ai_atlas_api.builder_models import BuilderLiteRequest, BuilderLiteResponse
from ai_atlas_api.catalog import CatalogError
from ai_atlas_api.catalog_models import ErrorResponse


def builder_router(service: BuilderLiteService) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1",
        tags=["builder-lite"],
        responses={
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )

    def no_parameters(request: Request) -> None:
        if request.query_params:
            raise CatalogError(
                422,
                "VALIDATION_ERROR",
                "Endpoint không nhận query parameters.",
                next(iter(request.query_params)),
            )

    @router.post(
        "/builder/candidates",
        response_model=BuilderLiteResponse,
        dependencies=[Depends(no_parameters)],
    )
    def candidates(request: Request, body: BuilderLiteRequest) -> BuilderLiteResponse:
        return BuilderLiteResponse(
            data=service.build(body),
            request_id=request.state.request_id,
        )

    return router
