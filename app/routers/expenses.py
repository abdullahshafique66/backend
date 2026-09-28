from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import delete, func, select

from .. import schemas
from ..deps import DB, CurrentUser
from ..models import Category, Expense
from ..services import calc

router = APIRouter(prefix="/expenses", tags=["expenses"])


def _check_category(db, user_id: str, category_id: str) -> None:
    if not db.scalar(select(Category.id).where(Category.id == category_id, Category.user_id == user_id)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Category nahi mili.")


def _own(db, user_id: str, expense_id: str) -> Expense:
    e = db.get(Expense, expense_id)
    if not e or e.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")
    return e


@router.get("", response_model=schemas.PaginatedExpenses)
def list_expenses(
    user: CurrentUser,
    db: DB,
    search: str | None = None,
    category_id: str | None = None,
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: date | None = None,
    min_amount: int | None = None,
    max_amount: int | None = None,
    sort: schemas.SortKey = "date_desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=5000)] = 10,
):
    return calc.query_expenses(db, user.id, search=search, category_id=category_id, start=from_, end=to,
                               min_amount=min_amount, max_amount=max_amount, sort=sort, page=page, page_size=page_size)


@router.get("/suggestions", response_model=list[schemas.Suggestion])
def suggestions(user: CurrentUser, db: DB):
    """Most-used item names (with their latest amount / category) for the Add Expense form."""
    counts = (
        select(func.lower(Expense.item_name).label("k"), func.count().label("n"), func.max(Expense.created_at).label("last"))
        .where(Expense.user_id == user.id)
        .group_by(func.lower(Expense.item_name))
        .order_by(func.count().desc())
        .limit(40)
        .subquery()
    )
    rows = db.execute(
        select(Expense).join(counts, (func.lower(Expense.item_name) == counts.c.k) & (Expense.created_at == counts.c.last))
        .where(Expense.user_id == user.id)
        .order_by(counts.c.n.desc())
    ).scalars().all()
    seen, out = set(), []
    for e in rows:
        if e.item_name.lower() in seen:
            continue
        seen.add(e.item_name.lower())
        out.append(schemas.Suggestion(item_name=e.item_name, category_id=e.category_id, amount=e.amount, unit=e.unit, quantity=e.quantity))
    return out


@router.post("", response_model=schemas.ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(body: schemas.ExpenseIn, user: CurrentUser, db: DB):
    _check_category(db, user.id, body.category_id)
    data = body.model_dump()
    if data["quantity"] is None:
        data["unit"] = None
    elif data["unit"] is None:
        data["unit"] = "piece"
    e = Expense(user_id=user.id, **data)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@router.patch("/{expense_id}", response_model=schemas.ExpenseOut)
def update_expense(expense_id: str, body: schemas.ExpensePatch, user: CurrentUser, db: DB):
    e = _own(db, user.id, expense_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("category_id"):
        _check_category(db, user.id, data["category_id"])
    for k, v in data.items():
        if k in ("item_name", "amount", "category_id", "date") and v is None:
            continue  # required fields can't be cleared
        setattr(e, k, v.strip() if k == "item_name" else v)
    if e.quantity is None:
        e.unit = None
    db.commit()
    db.refresh(e)
    return e


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: str, user: CurrentUser, db: DB):
    db.delete(_own(db, user.id, expense_id))
    db.commit()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_expenses(user: CurrentUser, db: DB):
    """Deletes all of the user's expenses (categories and budgets stay)."""
    db.execute(delete(Expense).where(Expense.user_id == user.id))
    db.commit()
