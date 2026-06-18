"""
Test Cases Endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.database import get_db
from common.db.models.user import User
from common.api.deps import get_current_active_user
from common.api.pagination import PaginationParams, PaginatedResponse
from common.utils.logger import get_logger
from features.functional.db.models.test_case import TestCaseStatus
from features.functional.schemas.test_case import (
    TestCaseCreate,
    TestCaseUpdate,
    TestCaseResponse,
    TestCaseWithSteps,
    GenerateTestCasesRequest,
)
from features.functional.schemas.test_case_import import TestCaseCsvImportResponse
from features.functional.services.test_case_service import TestCaseService

logger = get_logger("qastra.test")

router = APIRouter()


class BulkStatusRequest(BaseModel):
    project_id: int
    case_ids: List[int]
    status: TestCaseStatus


class PromoteAllDraftRequest(BaseModel):
    project_id: int


@router.get("/", response_model=PaginatedResponse[TestCaseResponse])
async def list_test_cases(
    project_id: int,
    requirement_id: Optional[int] = None,
    user_story_id: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    include_steps: bool = Query(False),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List test cases with filters."""
    service = TestCaseService(db)
    test_cases, total = await service.get_list(
        project_id=project_id,
        requirement_id=requirement_id,
        user_story_id=user_story_id,
        status=status,
        priority=priority,
        category=category,
        search=search,
        pagination=pagination,
        include_steps=include_steps,
    )
    
    return PaginatedResponse.create(
        items=test_cases,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/csv-template")
async def download_test_case_csv_template(
    current_user: User = Depends(get_current_active_user),
):
    """Download example CSV and column notes (UTF-8)."""
    from features.functional.services.test_case_csv_import import csv_template_text

    body = csv_template_text()
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="qastra-test-cases-template.csv"',
        },
    )


@router.post("/import-csv", response_model=TestCaseCsvImportResponse)
async def import_test_cases_csv(
    project_id: int = Form(...),
    dry_run: bool = Form(False),
    import_mode: str = Form("strict"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Import test cases and steps from one UTF-8 CSV (see GET /csv-template)."""
    from features.functional.services.analytics.access import assert_project_access

    await assert_project_access(db, current_user, project_id)
    content = await file.read()
    filename = getattr(file, "filename", "unknown")
    logger.info(
        "[import_csv] request project_id=%s user_id=%s filename=%r size_bytes=%d dry_run=%s mode=%s",
        project_id, current_user.id, filename, len(content), dry_run, import_mode,
    )
    service = TestCaseService(db)
    result = await service.import_test_cases_from_csv(
        project_id=project_id,
        created_by=current_user.id,
        file_bytes=content,
        dry_run=dry_run,
        import_mode=import_mode or "strict",
    )
    if result.errors and not result.created_cases:
        logger.warning(
            "[import_csv] failed project_id=%s filename=%r error_count=%d",
            project_id, filename, len(result.errors),
        )
    return result


@router.patch("/promote-all-draft", response_model=dict)
async def promote_all_draft_to_ready(
    body: PromoteAllDraftRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Promote every draft test case in a project to ready in a single query."""
    from features.functional.services.analytics.access import assert_project_access
    from sqlalchemy import update as sa_update
    from features.functional.db.models.test_case import TestCase as TestCaseModel

    await assert_project_access(db, current_user, body.project_id)
    result = await db.execute(
        sa_update(TestCaseModel)
        .where(
            TestCaseModel.project_id == body.project_id,
            TestCaseModel.status == TestCaseStatus.draft,
        )
        .values(status=TestCaseStatus.ready)
        .execution_options(synchronize_session="fetch")
    )
    await db.commit()
    promoted = result.rowcount  # type: ignore[attr-defined]
    logger.info(
        "[promote_all_draft] project_id=%s user_id=%s promoted=%d",
        body.project_id, current_user.id, promoted,
    )
    return {"promoted": promoted}


@router.patch("/bulk-status", response_model=dict)
async def bulk_update_test_case_status(
    body: BulkStatusRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update status for a batch of test cases (scoped to project_id for safety)."""
    from features.functional.services.analytics.access import assert_project_access
    from sqlalchemy import update as sa_update

    await assert_project_access(db, current_user, body.project_id)
    if not body.case_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="case_ids is empty.")
    if len(body.case_ids) > 1000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot update more than 1000 cases at once.",
        )

    from features.functional.db.models.test_case import TestCase as TestCaseModel
    result = await db.execute(
        sa_update(TestCaseModel)
        .where(
            TestCaseModel.id.in_(body.case_ids),
            TestCaseModel.project_id == body.project_id,
        )
        .values(status=body.status)
        .execution_options(synchronize_session="fetch")
    )
    await db.commit()
    updated = result.rowcount  # type: ignore[attr-defined]
    logger.info(
        "[bulk_status] project_id=%s user_id=%s status=%s requested=%d updated=%d",
        body.project_id, current_user.id, body.status.value, len(body.case_ids), updated,
    )
    return {"updated": updated, "status": body.status.value}


@router.post("/", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_test_case(
    test_case_data: TestCaseCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new test case."""
    service = TestCaseService(db)
    test_case = await service.create(test_case_data, created_by=current_user.id)
    return test_case


@router.get("/{test_case_id}", response_model=TestCaseWithSteps)
async def get_test_case(
    test_case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a test case by ID with all steps."""
    service = TestCaseService(db)
    test_case = await service.get_by_id_with_steps(test_case_id)
    
    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found",
        )
    
    return test_case


@router.put("/{test_case_id}", response_model=TestCaseResponse)
async def update_test_case(
    test_case_id: int,
    test_case_data: TestCaseUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a test case."""
    service = TestCaseService(db)
    test_case = await service.update(test_case_id, test_case_data)
    
    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found",
        )
    
    return test_case


@router.delete("/{test_case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_case(
    test_case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a test case."""
    service = TestCaseService(db)
    deleted = await service.delete(test_case_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found",
        )


@router.post("/generate", response_model=dict)
async def generate_test_cases(
    request: GenerateTestCasesRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate test cases using LLM from requirements or Jira stories."""
    from features.functional.services.test_case_generation_service import TestCaseGenerationService
    service = TestCaseGenerationService(db)
    result = await service.generate_test_cases(request)
    return result


@router.post("/{test_case_id}/generate-steps", response_model=dict)
async def generate_test_steps(
    test_case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate test steps for a test case using LLM."""
    from features.functional.services.test_step_generation_service import TestStepGenerationService
    service = TestStepGenerationService(db)
    result = await service.generate_test_steps(test_case_id)
    return result


@router.post("/{test_case_id}/regenerate-steps", response_model=dict)
async def regenerate_test_steps(
    test_case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate test steps for a test case (deletes existing steps first)."""
    from features.functional.services.test_step_generation_service import TestStepGenerationService
    service = TestStepGenerationService(db)
    result = await service.regenerate_test_steps(test_case_id)
    return result
