"""Request/response schemas. Field names match the frontend TypeScript types (snake_case)."""
from datetime import date as Date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Unit = Literal["piece", "kg", "gram", "liter", "dozen", "pack", "other"]
Icon = Literal[
    "grocery", "vegetables", "fruits", "dairy", "meat", "food", "bills", "transport",
    "household", "other", "health", "education", "gift", "phone",
]
Granularity = Literal["daily", "weekly", "monthly"]
SortKey = Literal["date_desc", "date_asc", "amount_desc", "amount_asc", "name_asc"]
ReportFormat = Literal["pdf", "excel", "csv"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Users / auth ----------
class UserOut(ORM):
    id: str
    name: str
    email: str
    avatar_url: str | None = None
    created_at: datetime


class SignupIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class SessionOut(BaseModel):
    token: str
    user: UserOut


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class ChangePasswordIn(BaseModel):
    current: str
    next: str = Field(min_length=8, max_length=128)


class ProfilePatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    # data: URL of a small (≤160px) avatar, or null to remove
    avatar_url: str | None = Field(default=None, max_length=300_000)


# ---------- Categories ----------
class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=24)
    icon: Icon = "other"
    color: str = Field(default="#86938C", pattern=r"^#[0-9A-Fa-f]{6}$")

    @field_validator("name")
    @classmethod
    def strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Category ka naam likhein.")
        return v


class CategoryPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=24)
    icon: Icon | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class CategoryOut(ORM):
    id: str
    user_id: str
    name: str
    icon: str
    color: str
    created_at: datetime


# ---------- Expenses ----------
class ExpenseIn(BaseModel):
    item_name: str = Field(min_length=1, max_length=120)
    quantity: float | None = Field(default=None, gt=0, le=100_000)
    unit: Unit | None = None
    amount: int = Field(gt=0, le=10_000_000)
    category_id: str
    date: Date
    note: str | None = Field(default=None, max_length=500)

    @field_validator("item_name")
    @classmethod
    def strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Item ka naam likhein.")
        return v


class ExpensePatch(BaseModel):
    item_name: str | None = Field(default=None, min_length=1, max_length=120)
    quantity: float | None = Field(default=None, gt=0, le=100_000)
    unit: Unit | None = None
    amount: int | None = Field(default=None, gt=0, le=10_000_000)
    category_id: str | None = None
    date: Date | None = None
    note: str | None = Field(default=None, max_length=500)


class ExpenseOut(ORM):
    id: str
    user_id: str
    item_name: str
    quantity: float | None
    unit: str | None
    amount: int
    category_id: str
    date: Date
    note: str | None
    created_at: datetime
    updated_at: datetime


class PaginatedExpenses(BaseModel):
    items: list[ExpenseOut]
    total: int
    page: int
    page_size: int
    total_amount: int


class Suggestion(BaseModel):
    item_name: str
    category_id: str
    amount: int
    unit: str | None
    quantity: float | None


# ---------- Budget ----------
class BudgetIn(BaseModel):
    amount: int = Field(gt=0, le=100_000_000)


class BudgetOut(ORM):
    id: str
    user_id: str
    amount: int
    month: int
    year: int


# ---------- Dashboard / analytics / reports ----------
class DashboardStats(BaseModel):
    today: int
    yesterday: int
    week: int
    last_week: int
    month: int
    last_month: int
    total_entries: int
    month_entries: int
    budget: BudgetOut | None


class SeriesPoint(BaseModel):
    key: str
    label: str
    total: int


class CategoryTotal(BaseModel):
    category_id: str
    name: str
    color: str
    icon: str
    total: int
    count: int
    share: float


class TopItem(BaseModel):
    item_name: str
    total: int
    count: int


class Analytics(BaseModel):
    from_: Date = Field(serialization_alias="from")
    to: Date
    total: int
    count: int
    average_per_day: float
    series: list[SeriesPoint]
    by_category: list[CategoryTotal]
    top_items: list[TopItem]


class Report(BaseModel):
    title: str
    period_label: str
    from_: Date = Field(serialization_alias="from")
    to: Date
    total_items: int
    total_expense: int
    by_category: list[CategoryTotal]
    expenses: list[ExpenseOut]
    generated_at: datetime


class ExportOut(BaseModel):
    user: UserOut
    categories: list[CategoryOut]
    expenses: list[ExpenseOut]
    budgets: list[BudgetOut]
