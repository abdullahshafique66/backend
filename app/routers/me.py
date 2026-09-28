from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from .. import schemas
from ..deps import DB, CurrentUser
from ..models import Budget, Category, Expense, User

router = APIRouter(tags=["account"])


@router.get("/me", response_model=schemas.UserOut)
def me(user: CurrentUser):
    return user


@router.patch("/me", response_model=schemas.UserOut)
def update_me(body: schemas.ProfilePatch, user: CurrentUser, db: DB):
    data = body.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        email = data["email"].lower()
        if email != user.email and db.scalar(select(User).where(User.email == email)):
            raise HTTPException(status.HTTP_409_CONFLICT, "Yeh email kisi aur account par hai.")
        data["email"] = email
    if "avatar_url" in data and data["avatar_url"] and not data["avatar_url"].startswith(("data:image/", "https://")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tasveer sahi format mein nahi.")
    for k, v in data.items():
        if k == "name" and v:
            v = v.strip()
        setattr(user, k, v)
    db.commit()
    return user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(user: CurrentUser, db: DB):
    # Expenses first (they reference categories), then everything else cascades with the user.
    for e in db.scalars(select(Expense).where(Expense.user_id == user.id)):
        db.delete(e)
    db.flush()
    db.delete(user)
    db.commit()


@router.get("/export", response_model=schemas.ExportOut)
def export_all(user: CurrentUser, db: DB):
    return schemas.ExportOut(
        user=schemas.UserOut.model_validate(user),
        categories=[schemas.CategoryOut.model_validate(c) for c in db.scalars(select(Category).where(Category.user_id == user.id))],
        expenses=[schemas.ExpenseOut.model_validate(e) for e in db.scalars(select(Expense).where(Expense.user_id == user.id).order_by(Expense.date))],
        budgets=[schemas.BudgetOut.model_validate(b) for b in db.scalars(select(Budget).where(Budget.user_id == user.id))],
    )
