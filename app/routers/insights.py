from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select

from .. import schemas
from ..deps import DB, CurrentUser, today
from ..models import Category
from ..services import calc, exporters

router = APIRouter(tags=["dashboard & reports"])
MAX_RANGE_DAYS = 3 * 366


def _range(start: date | None, end: date | None, default_days: int) -> tuple[date, date]:
    end = end or today()
    start = start or end - timedelta(days=default_days - 1)
    if start > end:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "'from' date 'to' se pehle honi chahiye.")
    if (end - start).days > MAX_RANGE_DAYS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Date range 3 saal se zyada nahi ho sakti.")
    return start, end


@router.get("/dashboard/stats", response_model=schemas.DashboardStats)
def dashboard_stats(user: CurrentUser, db: DB):
    return calc.dashboard_stats(db, user.id, today())


@router.get("/analytics", response_model=schemas.Analytics)
def analytics(
    user: CurrentUser,
    db: DB,
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: date | None = None,
    granularity: schemas.Granularity = "daily",
):
    start, end = _range(from_, to, 30)
    return calc.analytics(db, user.id, start, end, granularity)


@router.get("/reports", response_model=schemas.Report)
def report(
    user: CurrentUser,
    db: DB,
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: date | None = None,
    title: str = Query("Expense Report", max_length=80),
):
    start, end = _range(from_ or calc.month_start(today()), to, 30)
    return calc.build_report(db, user.id, start, end, title, today())


@router.get("/reports/export", response_class=Response, responses={200: {"content": {"application/pdf": {}, "text/csv": {}}}})
def export_report(
    user: CurrentUser,
    db: DB,
    format: schemas.ReportFormat = "pdf",
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: date | None = None,
    title: str = Query("Expense Report", max_length=80),
):
    start, end = _range(from_ or calc.month_start(today()), to, 30)
    rep = calc.build_report(db, user.id, start, end, title, today())
    names = {c.id: c.name for c in db.scalars(select(Category).where(Category.user_id == user.id))}
    base = f"apna-hisab-{start}_to_{end}"
    if format == "csv":
        data, mime, ext = exporters.to_csv(rep, names), "text/csv; charset=utf-8", "csv"
    elif format == "excel":
        data, mime, ext = exporters.to_xlsx(rep, names), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
    else:
        data, mime, ext = exporters.to_pdf(rep, names), "application/pdf", "pdf"
    return Response(content=data, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{base}.{ext}"'})
