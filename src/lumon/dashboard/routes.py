"""FastAPI routes for the local Lumon Dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from lumon import __version__
from lumon.dashboard.schemas import (
    BootstrapResponse,
    FeishuWebhookResponse,
    FeishuWebhookTestRequest,
    HealthResponse,
    InitializeWorkspaceRequest,
    InitializeWorkspaceResponse,
    RegisterWorkspaceRequest,
    RepositoryOverviewResponse,
    RepositoryResultResponse,
    WebhookTestResponse,
    WorkspaceOverviewResponse,
    WorkspaceResponse,
    WorkspaceSettingsResponse,
    WorkspaceSettingsUpdate,
)
from lumon.dashboard.service import (
    DashboardService,
    WorkspaceListItem,
    WorkspaceSettingsView,
)
from lumon.errors import InvalidInputError, LumonError, PreflightError, WorkspaceNotFoundError

# Route functions are consumed by FastAPI's runtime decorators.
# pyright cannot observe that registration and reports them as unused otherwise.
# pyright: reportUnusedFunction=false


def create_app(service: DashboardService | None = None) -> FastAPI:
    """Create a fresh FastAPI application with an isolated Dashboard service."""

    app = FastAPI(title="Lumon Dashboard", version=__version__)
    app.state.dashboard_service = service or DashboardService()
    router = APIRouter(prefix="/api")

    @router.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(ok=True, version=__version__)

    @router.get("/bootstrap", response_model=BootstrapResponse)
    def bootstrap(request: Request) -> BootstrapResponse:
        workspaces = _service(request).list_workspaces()
        return BootstrapResponse(
            version=__version__,
            workspace_count=len(workspaces),
            has_workspaces=bool(workspaces),
        )

    @router.get("/workspaces", response_model=list[WorkspaceResponse])
    def list_workspaces(request: Request) -> list[WorkspaceResponse]:
        return [_workspace_response(item) for item in _service(request).list_workspaces()]

    @router.post("/workspaces/register", response_model=WorkspaceResponse, status_code=201)
    def register_workspace(
        request: Request, payload: RegisterWorkspaceRequest
    ) -> WorkspaceResponse:
        service = _service(request)
        registration = service.register_workspace(_path(payload.path))
        item = next(
            item
            for item in service.list_workspaces()
            if item.registration.workspace_id == registration.workspace_id
        )
        return _workspace_response(item)

    @router.post(
        "/workspaces/initialize",
        response_model=InitializeWorkspaceResponse,
        status_code=201,
    )
    def initialize_workspace(
        request: Request, payload: InitializeWorkspaceRequest
    ) -> InitializeWorkspaceResponse:
        result, registration = _service(request).initialize_workspace(
            _path(payload.path),
            payload.name,
            tuple(payload.repositories),
        )
        return InitializeWorkspaceResponse(
            status=result.status,
            workspace=result.workspace,
            workspace_id=registration.workspace_id,
            repositories=[
                RepositoryResultResponse(
                    name=item.name,
                    path=item.path,
                    status=item.status,
                    branch=item.branch,
                    revision=item.revision,
                )
                for item in result.repositories
            ],
        )

    @router.get(
        "/workspaces/{workspace_id}/overview",
        response_model=WorkspaceOverviewResponse,
    )
    def workspace_overview(request: Request, workspace_id: UUID) -> WorkspaceOverviewResponse:
        overview = _service(request).overview(workspace_id)
        return WorkspaceOverviewResponse(
            workspace_id=overview.workspace_id,
            name=overview.name,
            path=overview.path,
            created_at=overview.created_at,
            lumon_version=overview.lumon_version,
            repositories=[
                RepositoryOverviewResponse(
                    name=item.name,
                    path=item.path,
                    branch=item.branch,
                    revision=item.revision,
                    health=item.health,
                    detail=item.detail,
                )
                for item in overview.repositories
            ],
        )

    @router.get(
        "/workspaces/{workspace_id}/settings",
        response_model=WorkspaceSettingsResponse,
    )
    def workspace_settings(request: Request, workspace_id: UUID) -> WorkspaceSettingsResponse:
        return _settings_response(_service(request).settings(workspace_id))

    @router.put(
        "/workspaces/{workspace_id}/settings",
        response_model=WorkspaceSettingsResponse,
    )
    def update_workspace_settings(
        request: Request,
        workspace_id: UUID,
        payload: WorkspaceSettingsUpdate,
    ) -> WorkspaceSettingsResponse:
        update = payload.feishu_webhook
        settings = _service(request).update_settings(
            workspace_id,
            enabled=update.enabled,
            url_provided="url" in update.model_fields_set,
            url=update.url,
        )
        return _settings_response(settings)

    @router.post(
        "/workspaces/{workspace_id}/settings/feishu/test",
        response_model=WebhookTestResponse,
    )
    def test_feishu_webhook(
        request: Request,
        workspace_id: UUID,
        payload: FeishuWebhookTestRequest,
    ) -> WebhookTestResponse:
        result = _service(request).test_feishu_webhook(
            workspace_id,
            url_provided="url" in payload.model_fields_set,
            url=payload.url,
        )
        return WebhookTestResponse(success=result.success, detail=result.detail)

    app.include_router(router)
    app.add_exception_handler(WorkspaceNotFoundError, cast(Any, _not_found_handler))
    app.add_exception_handler(LumonError, cast(Any, _lumon_error_handler))
    return app


def _service(request: Request) -> DashboardService:
    return cast(DashboardService, request.app.state.dashboard_service)


def _path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _workspace_response(item: WorkspaceListItem) -> WorkspaceResponse:
    registration = item.registration
    return WorkspaceResponse(
        workspace_id=registration.workspace_id,
        name=registration.name,
        path=registration.path,
        registered_at=registration.registered_at,
        health=item.health,
        detail=item.detail,
    )


def _settings_response(settings: WorkspaceSettingsView) -> WorkspaceSettingsResponse:
    webhook = settings.feishu_webhook
    return WorkspaceSettingsResponse(
        workspace_id=settings.workspace_id,
        feishu_webhook=FeishuWebhookResponse(
            enabled=webhook.enabled,
            configured=webhook.configured,
            masked_url=webhook.masked_url,
        ),
    )


def _error_response(error: LumonError, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": type(error).__name__,
                "message": str(error),
            }
        },
    )


async def _not_found_handler(_: Request, error: WorkspaceNotFoundError) -> JSONResponse:
    return _error_response(error, 404)


async def _lumon_error_handler(_: Request, error: LumonError) -> JSONResponse:
    status_code = 422 if isinstance(error, InvalidInputError) else 400
    if isinstance(error, PreflightError):
        status_code = 409
    return _error_response(error, status_code)
