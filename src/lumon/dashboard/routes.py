"""FastAPI routes for the local Lumon Dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from lumon import __version__
from lumon.dashboard.schemas import (
    AgentObservabilityResponse,
    AgentSettingsResponse,
    AgentSettingsUpdate,
    BootstrapResponse,
    FeishuWebhookResponse,
    FeishuWebhookTestRequest,
    FlowContentRequest,
    FlowDocumentResponse,
    FlowSummaryResponse,
    HealthResponse,
    InitializeWorkspaceRequest,
    InitializeWorkspaceResponse,
    RegisterWorkspaceRequest,
    RepositoryOverviewResponse,
    RepositoryResultResponse,
    WebhookTestResponse,
    WorkspaceFolderSelectionResponse,
    WorkspaceOverviewResponse,
    WorkspaceResponse,
    WorkspaceSettingsResponse,
    WorkspaceSettingsUpdate,
)
from lumon.dashboard.service import (
    AgentObservabilitySettingsUpdate,
    AgentSettingsView,
    DashboardService,
    FlowDocumentView,
    FlowSummaryView,
    WorkspaceListItem,
    WorkspaceSettingsView,
)
from lumon.dashboard.service import (
    AgentSettingsUpdate as AgentSettingsUpdateRequest,
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

    @router.get("/agent/settings", response_model=AgentSettingsResponse)
    def agent_settings(request: Request) -> AgentSettingsResponse:
        return _agent_settings_response(_service(request).agent_settings())

    @router.put("/agent/settings", response_model=AgentSettingsResponse)
    def update_agent_settings(
        request: Request, payload: AgentSettingsUpdate
    ) -> AgentSettingsResponse:
        observability = payload.observability
        settings = _service(request).update_agent_settings(
            AgentSettingsUpdateRequest(
                enabled=payload.enabled,
                default_workspace_id=payload.default_workspace_id,
                agent_model=payload.agent_model,
                agent_reasoning_effort=payload.agent_reasoning_effort,
                feishu_app_id=payload.feishu_app_id,
                feishu_app_secret=payload.feishu_app_secret,
                observability=AgentObservabilitySettingsUpdate(
                    enabled=observability.enabled,
                    base_url=observability.base_url,
                    sample_rate=observability.sample_rate,
                    public_key=observability.public_key,
                    secret_key=observability.secret_key,
                    clear_credentials=observability.clear_credentials,
                ),
            )
        )
        return _agent_settings_response(settings)

    @router.get("/workspaces", response_model=list[WorkspaceResponse])
    def list_workspaces(request: Request) -> list[WorkspaceResponse]:
        return [_workspace_response(item) for item in _service(request).list_workspaces()]

    @router.post(
        "/workspaces/select-folder",
        response_model=WorkspaceFolderSelectionResponse,
    )
    def select_workspace_folder(request: Request) -> WorkspaceFolderSelectionResponse:
        path = _service(request).select_workspace_folder()
        return WorkspaceFolderSelectionResponse(path=path, cancelled=path is None)

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

    @router.get(
        "/workspaces/{workspace_id}/flows",
        response_model=list[FlowSummaryResponse],
    )
    def list_flows(request: Request, workspace_id: UUID) -> list[FlowSummaryResponse]:
        return [_flow_summary_response(item) for item in _service(request).flows(workspace_id)]

    @router.post(
        "/workspaces/{workspace_id}/flows",
        response_model=FlowDocumentResponse,
        status_code=201,
    )
    def create_flow(
        request: Request, workspace_id: UUID, payload: FlowContentRequest
    ) -> FlowDocumentResponse:
        return _flow_document_response(_service(request).create_flow(workspace_id, payload.content))

    @router.get(
        "/workspaces/{workspace_id}/flows/{flow_id}",
        response_model=FlowDocumentResponse,
    )
    def get_flow(request: Request, workspace_id: UUID, flow_id: str) -> FlowDocumentResponse:
        return _flow_document_response(_service(request).flow(workspace_id, flow_id))

    @router.put(
        "/workspaces/{workspace_id}/flows/{flow_id}",
        response_model=FlowDocumentResponse,
    )
    def update_flow(
        request: Request,
        workspace_id: UUID,
        flow_id: str,
        payload: FlowContentRequest,
    ) -> FlowDocumentResponse:
        return _flow_document_response(
            _service(request).update_flow(workspace_id, flow_id, payload.content)
        )

    @router.delete("/workspaces/{workspace_id}/flows/{flow_id}", status_code=204)
    def delete_flow(request: Request, workspace_id: UUID, flow_id: str) -> None:
        _service(request).delete_flow(workspace_id, flow_id)

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


def _flow_summary_response(summary: FlowSummaryView) -> FlowSummaryResponse:
    return FlowSummaryResponse(
        flow_id=summary.flow_id,
        name=summary.name,
        enabled=summary.enabled,
        brief=summary.brief,
        path=summary.path,
        valid=summary.valid,
        error=summary.error,
    )


def _flow_document_response(document: FlowDocumentView) -> FlowDocumentResponse:
    return FlowDocumentResponse(
        flow_id=document.flow_id,
        name=document.name,
        enabled=document.enabled,
        brief=document.brief,
        path=document.path,
        valid=document.valid,
        error=document.error,
        content=document.content,
    )


def _agent_settings_response(settings: AgentSettingsView) -> AgentSettingsResponse:
    # The service returns a typed view; keeping the conversion here ensures the
    # HTTP response never grows a path to credential values by accident.
    observability = settings.observability
    return AgentSettingsResponse(
        enabled=settings.enabled,
        default_workspace_id=settings.default_workspace_id,
        agent_provider=settings.agent_provider,
        agent_model=settings.agent_model,
        agent_reasoning_effort=settings.agent_reasoning_effort,
        feishu_app_id=settings.feishu_app_id,
        feishu_app_configured=settings.feishu_app_configured,
        feishu_app_secret_masked=settings.feishu_app_secret_masked,
        observability=AgentObservabilityResponse(
            enabled=observability.enabled,
            provider=observability.provider,
            base_url=observability.base_url,
            sample_rate=observability.sample_rate,
            public_key_configured=observability.public_key_configured,
            secret_key_configured=observability.secret_key_configured,
            public_key_masked=observability.public_key_masked,
            secret_key_masked=observability.secret_key_masked,
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
