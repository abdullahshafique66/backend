"""Default categories for every new user, plus the demo account with realistic Pakistani household data."""
import random
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Budget, Category, Expense, User
from ..security import hash_password

DEFAULT_CATEGORIES = [
    ("Grocery", "grocery", "#087F5B"),
    ("Vegetables", "vegetables", "#5E9E3F"),
    ("Fruits", "fruits", "#E07A3F"),
    ("Dairy", "dairy", "#4A86C8"),
    ("Meat", "meat", "#C4524E"),
    ("Food", "food", "#F4A340"),
    ("Bills", "bills", "#7A66C4"),
    ("Transport", "transport", "#2A9D96"),
    ("Household", "household", "#B08A3E"),
    ("Other", "other", "#86938C"),
]

DEMO_EMAIL = "ayesha@example.pk"
DEMO_PASSWORD = "demo1234"


def create_default_categories(db: Session, user: User) -> dict[str, Category]:
    cats = {}
    for name, icon, color in DEFAULT_CATEGORIES:
        c = Category(user_id=user.id, name=name, icon=icon, color=color)
        db.add(c)
        cats[icon] = c
    db.flush()
    return cats


# (days ago, item, amount, category key, qty, unit, note)
RECENT = [
    (0, "Doodh", 180, "dairy", 1, "liter", None), (0, "Aloo", 120, "vegetables", 2, "kg", None),
    (0, "Tamatar", 150, "vegetables", 1, "kg", None), (0, "Chicken", 650, "meat", 1, "kg", None),
    (0, "Naan", 150, "food", 6, "piece", "Tandoor wale se"),
    (1, "Doodh", 180, "dairy", 1, "liter", None), (1, "Sabzi", 350, "vegetables", None, None, "Bhindi, palak, dhania"),
    (1, "Rickshaw", 250, "transport", None, None, "Bazaar aana jana"),
    (2, "Doodh", 180, "dairy", 1, "liter", None), (2, "Atta", 1800, "grocery", 10, "kg", None), (2, "Pyaz", 100, "vegetables", 1, "kg", None),
    (3, "Doodh", 180, "dairy", 1, "liter", None), (3, "Kele", 220, "fruits", 1, "dozen", None), (3, "Rickshaw", 250, "transport", None, None, None),
    (4, "Doodh", 180, "dairy", 1, "liter", None), (4, "Dahi", 160, "dairy", 1, "kg", None), (4, "Beef", 1100, "meat", 1, "kg", None),
    (5, "Doodh", 180, "dairy", 1, "liter", None), (5, "Chai Patti", 450, "grocery", 1, "pack", None), (5, "Anday", 390, "dairy", 1, "dozen", None),
    (6, "Doodh", 180, "dairy", 1, "liter", None), (6, "Surf Excel", 650, "household", 1, "pack", None),
    (6, "Samosay", 150, "food", 6, "piece", None), (6, "Sabzi", 250, "vegetables", None, None, None),
    (7, "Doodh", 180, "dairy", 1, "liter", None), (7, "Bijli Bill", 5800, "bills", None, None, "LESCO"),
    (8, "Chicken", 650, "meat", 1, "kg", None), (9, "Doodh", 180, "dairy", 1, "liter", None), (9, "Chawal", 1250, "grocery", 5, "kg", "Basmati"),
    (10, "Gas Bill", 2400, "bills", None, None, "SNGPL"), (11, "Sabzi", 350, "vegetables", None, None, None), (11, "Rickshaw", 250, "transport", None, None, None),
    (12, "Doodh", 200, "dairy", 1, "liter", "Naya doodh wala"), (12, "Seb", 280, "fruits", 1, "kg", None), (13, "Qeema", 1100, "meat", 1, "kg", None),
    (14, "Cooking Oil", 2650, "grocery", 5, "liter", None), (15, "Mobile Load", 500, "bills", None, None, None),
    (16, "Doodh", 180, "dairy", 1, "liter", None), (16, "Daal Masoor", 380, "grocery", 1, "kg", None),
    (18, "Biryani", 700, "food", 2, "piece", "Friday dinner"), (19, "Chicken", 650, "meat", 1, "kg", None),
    (20, "Internet Bill", 2500, "bills", None, None, None), (21, "Petrol", 2000, "transport", 7, "liter", None),
    (22, "Aam", 470, "fruits", 2, "kg", None), (23, "Sabzi", 400, "vegetables", None, None, None), (23, "Doodh", 180, "dairy", 1, "liter", None),
    (25, "Cheeni", 300, "grocery", 2, "kg", None), (27, "Sabun aur Shampoo", 450, "household", None, None, None),
]
TEMPLATES = [
    ("Doodh", 180, "dairy", 1, "liter"), ("Doodh", 180, "dairy", 1, "liter"), ("Sabzi", 320, "vegetables", None, None),
    ("Aloo", 120, "vegetables", 2, "kg"), ("Tamatar", 160, "vegetables", 1, "kg"), ("Pyaz", 110, "vegetables", 1, "kg"),
    ("Chicken", 640, "meat", 1, "kg"), ("Rickshaw", 250, "transport", None, None), ("Naan", 150, "food", 6, "piece"),
    ("Dahi", 160, "dairy", 1, "kg"), ("Kele", 200, "fruits", 1, "dozen"), ("Anday", 380, "dairy", 1, "dozen"),
    ("Samosay", 150, "food", 6, "piece"), ("Aam", 450, "fruits", 2, "kg"),
]
MONTHLY = [
    ("Bijli Bill", 6400, "bills", None, None, 7), ("Gas Bill", 1900, "bills", None, None, 10), ("Internet Bill", 2500, "bills", None, None, 20),
    ("Atta", 1750, "grocery", 10, "kg", 3), ("Chawal", 1250, "grocery", 5, "kg", 12), ("Cooking Oil", 2600, "grocery", 5, "liter", 16),
    ("Petrol", 2000, "transport", 7, "liter", 21), ("Beef", 1100, "meat", 1, "kg", 14), ("Surf Excel", 620, "household", 1, "pack", 18),
]


def seed_expenses(db: Session, user: User, cats: dict[str, Category], today: date) -> None:
    n = 0

    def add(off, item, amount, key, qty, unit, note=None):
        nonlocal n
        n += 1
        d = today - timedelta(days=off)
        ts = datetime.combine(d, time(8 + n % 12, (n * 7) % 60), tzinfo=timezone.utc)
        db.add(Expense(user_id=user.id, item_name=item, amount=amount, category_id=cats[key].id, quantity=qty,
                       unit=unit if qty else None, date=d, note=note, created_at=ts, updated_at=ts))

    for row in RECENT:
        add(*row)
    rnd = random.Random(2026)
    for off in range(28, 96):
        for _ in range(1 + int(rnd.random() * 2.4)):
            item, amt, key, qty, unit = rnd.choice(TEMPLATES)
            add(off, item, amt + round((rnd.random() - 0.5) * 0.16 * amt / 10) * 10, key, qty, unit)
        for item, amt, key, qty, unit, cyc in MONTHLY:
            if (off - 28) % 30 == cyc:
                add(off, item, amt + round((rnd.random() - 0.5) * 30) * 10, key, qty, unit)


def ensure_demo_user(db: Session, today: date) -> None:
    if db.scalar(select(User).where(User.email == DEMO_EMAIL)):
        return
    user = User(name="Ayesha Khan", email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
    db.add(user)
    db.flush()
    cats = create_default_categories(db, user)
    seed_expenses(db, user, cats, today)
    db.add(Budget(user_id=user.id, amount=50000, month=today.month, year=today.year))
    db.commit()
