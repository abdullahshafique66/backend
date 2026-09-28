from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select, update

from .. import schemas
from ..deps import DB, CurrentUser
from ..models import Category, Expense

router = APIRouter(prefix="/categories", tags=["categories"])


def _own(db, user_id: str, cid: str) -> Category:
    c = db.get(Category, cid)
    if not c or c.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    return c


def _name_taken(db, user_id: str, name: str, exclude: str | None = None) -> bool:
    q = select(Category.id).where(Category.user_id == user_id, func.lower(Category.name) == name.lower())
    if exclude:
        q = q.where(Category.id != exclude)
    return db.scalar(q) is not None


@router.get("", response_model=list[schemas.CategoryOut])
def list_categories(user: CurrentUser, db: DB):
    return db.scalars(select(Category).where(Category.user_id == user.id).order_by(Category.created_at, Category.name)).all()


@router.post("", response_model=schemas.CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(body: schemas.CategoryIn, user: CurrentUser, db: DB):
    if _name_taken(db, user.id, body.name):
        raise HTTPException(status.HTTP_409_CONFLICT, "Is naam ki category pehle se maujood hai.")
    c = Category(user_id=user.id, **body.model_dump())
    db.add(c)
    db.commit()
    return c


@router.patch("/{category_id}", response_model=schemas.CategoryOut)
def update_category(category_id: str, body: schemas.CategoryPatch, user: CurrentUser, db: DB):
    c = _own(db, user.id, category_id)
    data = body.model_dump(exclude_unset=True, exclude_none=True)
    if "name" in data:
        data["name"] = data["name"].strip()
        if _name_taken(db, user.id, data["name"], exclude=c.id):
            raise HTTPException(status.HTTP_409_CONFLICT, "Is naam ki category pehle se maujood hai.")
    for k, v in data.items():
        setattr(c, k, v)
    db.commit()
    return c


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: str, user: CurrentUser, db: DB):
    """Expenses in the deleted category move to "Other" — no record is ever lost."""
    c = _own(db, user.id, category_id)
    others = db.scalars(select(Category).where(Category.user_id == user.id, Category.id != c.id)).all()
    target = next((x for x in others if x.icon == "other"), None) or (others[0] if others else None)
    if target is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kam az kam ek category honi chahiye.")
    db.execute(update(Expense).where(Expense.category_id == c.id).values(category_id=target.id))
    db.delete(c)
    db.commit()
