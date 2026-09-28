"""The automatic hisab — same logic as the frontend's src/services/calc.ts, run on the server."""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..models import Budget, Category, Expense
from .. import schemas

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def month_start(d: date) -> date:
    return d.replace(day=1)


def month_end(d: date) -> date:
    nxt = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return nxt - timedelta(days=1)


def short(d: date) -> str:
    return f"{d.day} {MONTHS[d.month - 1][:3]}"


def sum_between(db: Session, user_id: str, start: date, end: date) -> tuple[int, int]:
    total, count = db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0), func.count(Expense.id)).where(
            Expense.user_id == user_id, Expense.date >= start, Expense.date <= end
        )
    ).one()
    return int(total), int(count)


def expenses_between(db: Session, user_id: str, start: date, end: date) -> list[Expense]:
    return list(
        db.scalars(
            select(Expense)
            .where(Expense.user_id == user_id, Expense.date >= start, Expense.date <= end)
            .order_by(Expense.date, Expense.created_at)
        )
    )


def dashboard_stats(db: Session, user_id: str, today: date) -> schemas.DashboardStats:
    ms = month_start(today)
    prev_end = ms - timedelta(days=1)
    prev_start = month_start(prev_end)
    prev_same_day = prev_start.replace(day=min(today.day, prev_end.day))
    month_total, month_count = sum_between(db, user_id, ms, today)
    budget = db.scalar(select(Budget).where(Budget.user_id == user_id, Budget.year == today.year, Budget.month == today.month))
    return schemas.DashboardStats(
        today=sum_between(db, user_id, today, today)[0],
        yesterday=sum_between(db, user_id, today - timedelta(days=1), today - timedelta(days=1))[0],
        week=sum_between(db, user_id, today - timedelta(days=6), today)[0],
        last_week=sum_between(db, user_id, today - timedelta(days=13), today - timedelta(days=7))[0],
        month=month_total,
        last_month=sum_between(db, user_id, prev_start, prev_same_day)[0],
        total_entries=month_count,
        month_entries=month_count,
        budget=schemas.BudgetOut.model_validate(budget) if budget else None,
    )


def query_expenses(db: Session, user_id: str, *, search: str | None, category_id: str | None, start: date | None, end: date | None,
                   min_amount: int | None, max_amount: int | None, sort: str, page: int, page_size: int) -> schemas.PaginatedExpenses:
    conds = [Expense.user_id == user_id]
    stmt = select(Expense)
    if category_id and category_id != "all":
        conds.append(Expense.category_id == category_id)
    if start:
        conds.append(Expense.date >= start)
    if end:
        conds.append(Expense.date <= end)
    if min_amount is not None:
        conds.append(Expense.amount >= min_amount)
    if max_amount is not None:
        conds.append(Expense.amount <= max_amount)
    if search and search.strip():
        like = f"%{search.strip().lower()}%"
        stmt = stmt.join(Category, Category.id == Expense.category_id)
        conds.append(or_(func.lower(Expense.item_name).like(like), func.lower(func.coalesce(Expense.note, "")).like(like), func.lower(Category.name).like(like)))
    stmt = stmt.where(*conds)

    sub = stmt.subquery()
    count_stmt = select(func.count(), func.coalesce(func.sum(sub.c.amount), 0)).select_from(sub)
    total, total_amount = db.execute(count_stmt).one()

    order = {
        "date_asc": (Expense.date.asc(), Expense.created_at.asc()),
        "amount_desc": (Expense.amount.desc(), Expense.date.desc()),
        "amount_asc": (Expense.amount.asc(), Expense.date.desc()),
        "name_asc": (func.lower(Expense.item_name).asc(), Expense.date.desc()),
    }.get(sort, (Expense.date.desc(), Expense.created_at.desc()))
    pages = max(1, -(-int(total) // page_size))
    page = min(max(1, page), pages)
    items = db.scalars(stmt.order_by(*order).offset((page - 1) * page_size).limit(page_size)).all()
    return schemas.PaginatedExpenses(
        items=[schemas.ExpenseOut.model_validate(e) for e in items],
        total=int(total),
        page=page,
        page_size=page_size,
        total_amount=int(total_amount),
    )


def category_totals(rows: list[Expense], categories: list[Category]) -> list[schemas.CategoryTotal]:
    total = sum(e.amount for e in rows) or 1
    agg: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for e in rows:
        agg[e.category_id][0] += e.amount
        agg[e.category_id][1] += 1
    by_id = {c.id: c for c in categories}
    other = next((c for c in categories if c.icon == "other"), None)
    out = []
    for cid, (t, n) in agg.items():
        c = by_id.get(cid) or other
        out.append(schemas.CategoryTotal(
            category_id=cid, name=c.name if c else "Other", color=c.color if c else "#86938C",
            icon=c.icon if c else "other", total=t, count=n, share=t / total,
        ))
    return sorted(out, key=lambda x: -x.total)


def build_series(rows: list[Expense], start: date, end: date, g: str) -> list[schemas.SeriesPoint]:
    pts: list[schemas.SeriesPoint] = []
    if g == "daily":
        by_day: dict[date, int] = defaultdict(int)
        for e in rows:
            by_day[e.date] += e.amount
        d = start
        while d <= end:
            pts.append(schemas.SeriesPoint(key=d.isoformat(), label=short(d), total=by_day.get(d, 0)))
            d += timedelta(days=1)
    elif g == "weekly":
        e_ = end
        while e_ >= start:
            s_ = max(start, e_ - timedelta(days=6))
            pts.insert(0, schemas.SeriesPoint(key=s_.isoformat(), label=short(s_), total=sum(x.amount for x in rows if s_ <= x.date <= e_)))
            e_ -= timedelta(days=7)
    else:
        m = month_start(start)
        while m <= end:
            me = min(month_end(m), end)
            ms = max(m, start)
            pts.append(schemas.SeriesPoint(key=m.isoformat(), label=f"{MONTHS[m.month - 1][:3]} {str(m.year)[2:]}", total=sum(x.amount for x in rows if ms <= x.date <= me)))
            m = month_end(m) + timedelta(days=1)
    return pts


def analytics(db: Session, user_id: str, start: date, end: date, g: str) -> schemas.Analytics:
    rows = expenses_between(db, user_id, start, end)
    cats = list(db.scalars(select(Category).where(Category.user_id == user_id)))
    total = sum(e.amount for e in rows)
    items: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for e in rows:
        items[e.item_name.strip()][0] += e.amount
        items[e.item_name.strip()][1] += 1
    top = sorted(([k, v[0], v[1]] for k, v in items.items()), key=lambda x: -x[1])[:6]
    return schemas.Analytics(
        from_=start, to=end, total=total, count=len(rows),
        average_per_day=total / ((end - start).days + 1),
        series=build_series(rows, start, end, g),
        by_category=category_totals(rows, cats),
        top_items=[schemas.TopItem(item_name=k, total=t, count=n) for k, t, n in top],
    )


def period_label(start: date, end: date, today: date) -> str:
    if start == month_start(start) and (end == month_end(start) or (end == today and start.month == end.month and start.year == end.year)):
        return f"{MONTHS[start.month - 1]} {start.year}"
    left = short(start) + (f" {start.year}" if start.year != end.year else "")
    return f"{left} – {short(end)} {end.year}"


def build_report(db: Session, user_id: str, start: date, end: date, title: str, today: date) -> schemas.Report:
    rows = expenses_between(db, user_id, start, end)
    cats = list(db.scalars(select(Category).where(Category.user_id == user_id)))
    return schemas.Report(
        title=title, period_label=period_label(start, end, today), from_=start, to=end,
        total_items=len(rows), total_expense=sum(e.amount for e in rows),
        by_category=category_totals(rows, cats),
        expenses=[schemas.ExpenseOut.model_validate(e) for e in rows],
        generated_at=datetime.now(timezone.utc),
    )
