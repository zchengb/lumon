"""FastAPI routes for the local Lumon Dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from lumon import __version__
from lumon.dashboard.schemas import (
    AgentObservabilityResponse,
    AgentSettingsResponse,
    AgentSettingsUpdate,
    AutoDeliveryResponse,
    AutoScanResponse,
    BootstrapResponse,
    CapabilityContentRequest,
    CapabilityDocumentResponse,
    CapabilitySummaryResponse,
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
    ScanFindingResponse,
    ScanRunResponse,
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
    CapabilityDocumentView,
    CapabilitySummaryView,
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
from lumon.scan.model import ScanFinding, ScanRun

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
        "/workspaces/{workspace_id}/scans",
        response_model=list[ScanRunResponse],
    )
    def list_scans(request: Request, workspace_id: UUID) -> list[ScanRunResponse]:
        return [_scan_response(item) for item in _service(request).scans(workspace_id)]

    @router.post(
        "/workspaces/{workspace_id}/scans",
        response_model=ScanRunResponse,
        status_code=201,
    )
    def start_scan(request: Request, workspace_id: UUID) -> ScanRunResponse:
        return _scan_response(_service(request).start_scan(workspace_id))

    @router.get("/workspaces/{workspace_id}/scans/{run_id}/artifacts/{kind}")
    def scan_artifact(
        request: Request,
        workspace_id: UUID,
        run_id: str,
        kind: str,
    ) -> FileResponse:
        path = _service(request).scan_artifact(workspace_id, run_id, kind)
        media_type = "application/pdf" if kind == "pdf" else "text/html"
        return FileResponse(path, media_type=media_type, filename=path.name)

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

    @router.get(
        "/workspaces/{workspace_id}/capabilities",
        response_model=list[CapabilitySummaryResponse],
    )
    def list_capabilities(
        request: Request,
        workspace_id: UUID,
    ) -> list[CapabilitySummaryResponse]:
        return [
            _capability_summary_response(item)
            for item in _service(request).capabilities(workspace_id)
        ]

    @router.post(
        "/workspaces/{workspace_id}/capabilities",
        response_model=CapabilityDocumentResponse,
        status_code=201,
    )
    def create_capability(
        request: Request,
        workspace_id: UUID,
        payload: CapabilityContentRequest,
    ) -> CapabilityDocumentResponse:
        return _capability_document_response(
            _service(request).create_capability(workspace_id, payload.content)
        )

    @router.get(
        "/workspaces/{workspace_id}/capabilities/{capability_id}",
        response_model=CapabilityDocumentResponse,
    )
    def get_capability(
        request: Request,
        workspace_id: UUID,
        capability_id: str,
    ) -> CapabilityDocumentResponse:
        return _capability_document_response(
            _service(request).capability(workspace_id, capability_id)
        )

    @router.put(
        "/workspaces/{workspace_id}/capabilities/{capability_id}",
        response_model=CapabilityDocumentResponse,
    )
    def update_capability(
        request: Request,
        workspace_id: UUID,
        capability_id: str,
        payload: CapabilityContentRequest,
    ) -> CapabilityDocumentResponse:
        return _capability_document_response(
            _service(request).update_capability(
                workspace_id,
                capability_id,
                payload.content,
            )
        )

    @router.delete(
        "/workspaces/{workspace_id}/capabilities/{capability_id}",
        status_code=204,
    )
    def delete_capability(
        request: Request,
        workspace_id: UUID,
        capability_id: str,
    ) -> None:
        _service(request).delete_capability(workspace_id, capability_id)

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
        auto_delivery = payload.auto_delivery
        auto_scan = payload.auto_scan
        settings = _service(request).update_settings(
            workspace_id,
            enabled=update.enabled,
            url_provided="url" in update.model_fields_set,
            url=update.url,
            auto_delivery_enabled=(auto_delivery.enabled if auto_delivery is not None else None),
            auto_delivery_trigger_hooks=(
                tuple(auto_delivery.trigger_hooks)
                if auto_delivery is not None and auto_delivery.trigger_hooks is not None
                else None
            ),
            auto_delivery_schedule_expression=(
                auto_delivery.schedule_expression if auto_delivery is not None else None
            ),
            auto_scan_enabled=(auto_scan.enabled if auto_scan is not None else None),
            auto_scan_lookback_days=(auto_scan.lookback_days if auto_scan is not None else None),
            auto_scan_trigger_hooks=(
                tuple(auto_scan.trigger_hooks)
                if auto_scan is not None and auto_scan.trigger_hooks is not None
                else None
            ),
            auto_scan_schedule_expression=(
                auto_scan.schedule_expression if auto_scan is not None else None
            ),
            auto_scan_workflow_description=(
                auto_scan.workflow_description if auto_scan is not None else None
            ),
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
        auto_delivery=AutoDeliveryResponse(
            enabled=settings.auto_delivery.enabled,
            trigger_hooks=list(settings.auto_delivery.trigger_hooks),
            schedule_expression=settings.auto_delivery.schedule_expression,
        ),
        auto_scan=AutoScanResponse(
            enabled=settings.auto_scan.enabled,
            lookback_days=settings.auto_scan.lookback_days,
            trigger_hooks=list(settings.auto_scan.trigger_hooks),
            schedule_expression=settings.auto_scan.schedule_expression,
            workflow_description=settings.auto_scan.workflow_description,
        ),
    )


def _scan_response(run: ScanRun) -> ScanRunResponse:
    return ScanRunResponse(
        run_id=run.run_id,
        state=run.state.value,
        phase=run.phase,
        started_at=run.started_at.isoformat(),
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
        lookback_days=run.lookback_days,
        repositories_scanned=run.repositories_scanned,
        repositories_failed=run.repositories_failed,
        findings=[_finding_response(finding) for finding in run.findings],
        failures=list(run.failures),
        hook_results=list(run.hook_results),
        html_available=run.html_path is not None,
        pdf_available=run.pdf_path is not None,
        duration_seconds=run.duration_seconds,
    )


def _finding_response(finding: ScanFinding) -> ScanFindingResponse:
    return ScanFindingResponse(
        title=finding.title,
        severity=finding.severity,
        repository=finding.repository,
        impact=finding.impact,
        trigger=finding.trigger,
        file=finding.file,
        line_range=finding.line_range,
        code_snippet=finding.code_snippet,
        suggestion=finding.suggestion,
        root_cause=finding.root_cause,
        validation=finding.validation,
        issue_id=finding.issue_id,
        issue_status=finding.issue_status,
        pr_url=finding.pr_url,
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


def _capability_summary_response(
    summary: CapabilitySummaryView,
) -> CapabilitySummaryResponse:
    return CapabilitySummaryResponse(
        capability_id=summary.capability_id,
        name=summary.name,
        enabled=summary.enabled,
        brief=summary.brief,
        path=summary.path,
        valid=summary.valid,
        error=summary.error,
    )


def _capability_document_response(
    document: CapabilityDocumentView,
) -> CapabilityDocumentResponse:
    return CapabilityDocumentResponse(
        capability_id=document.capability_id,
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
