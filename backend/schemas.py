from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# --- Auth ---
class UserRegister(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=4, max_length=50)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str
    username: str
    user_id: int


# --- Bills ---
class BillCreate(BaseModel):
    type: str  # expense / income
    amount: float
    category_id: int
    category_name: str
    payment_method: str = "wechat"
    remark: str = ""
    date: str
    time: str


class BillUpdate(BaseModel):
    type: Optional[str] = None
    amount: Optional[float] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    payment_method: Optional[str] = None
    remark: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None


class BillOut(BaseModel):
    id: int
    user_id: int
    type: str
    amount: float
    category_id: int
    category_name: str
    payment_method: str
    remark: str
    date: str
    time: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Categories ---
class CategoryCreate(BaseModel):
    type: str
    name: str
    icon: str = "📦"
    color: str = "#5cb8a0"
    sort_order: int = 0


class CategoryOut(BaseModel):
    id: int
    type: str
    name: str
    icon: str
    color: str
    is_custom: bool
    sort_order: int

    class Config:
        from_attributes = True


# --- Fitness ---
class FitnessCreate(BaseModel):
    exercise_type: str
    duration_minutes: int
    calories: int = 0
    date: str
    time: str
    note: str = ""


class FitnessOut(BaseModel):
    id: int
    exercise_type: str
    duration_minutes: int
    calories: int
    date: str
    time: str
    note: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Settings ---
class SettingsOut(BaseModel):
    monthly_budget: float = 0
    fitness_daily_goal_minutes: int = 30
    fitness_daily_goal_calories: int = 300

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    monthly_budget: Optional[float] = None
    fitness_daily_goal_minutes: Optional[int] = None
    fitness_daily_goal_calories: Optional[int] = None


# --- Stats ---
class MonthlyStats(BaseModel):
    expense: float = 0
    income: float = 0
    balance: float = 0


class CategoryStats(BaseModel):
    category_id: int
    category_name: str
    amount: float
    percentage: float = 0
    color: str = "#5cb8a0"


# --- Data ---
class ExportData(BaseModel):
    bills: List
    fitness: List
    settings: dict
