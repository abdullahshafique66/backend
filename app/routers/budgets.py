from fastapi import APIRouter, HTTPException, Path, status
from sqlalchemy import select

from .. import schemas
from ..deps import DB, CurrentUser, today
from ..models import Budget

router = APIRouter(prefix="/budgets", tags=["budget"])


@router.get("/current", response_model=schemas.BudgetOut | None)
def current_budget(user: CurrentUser, db: DB):
    t = today()
    return db.scalar(select(Budget).where(Budget.user_id == user.id, Budget.year == t.year, Budget.month == t.month))


@router.put("/{year}/{month}", response_model=schemas.BudgetOut)
def set_budget(body: schemas.BudgetIn, user: CurrentUser, db: DB, year: int = Path(ge=2000, le=2100), month: int = Path(ge=1, le=12)):
    b = db.scalar(select(Budget).where(Budget.user_id == user.id, Budget.year == year, Budget.month == month))
    if b:
        b.amount = body.amount
    else:
        b = Budget(user_id=user.id, amount=body.amount, year=year, month=month)
        db.add(b)
    db.commit()
    return b
