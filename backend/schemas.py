from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Literal
from datetime import datetime, timezone


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


# --- Memory records ---
class MemoryCreate(BaseModel):
    source: Literal["manual", "coros"] = "manual"
    source_id: str | None = Field(default=None, min_length=1, max_length=200)
    occurred_at: datetime
    text: str = Field(default="", max_length=10000)
    hidden: bool = False

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value):
        if value.utcoffset() is None:
            raise ValueError("时间必须包含时区")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def valid_source(self):
        if self.source_id is not None and not self.source_id.strip():
            raise ValueError("来源 ID 不能为空")
        if self.source == "coros" and not self.source_id:
            raise ValueError("高驰记录需要来源 ID")
        return self


class MemorySuppressionInput(BaseModel):
    source: Literal["coros"]
    source_id: str = Field(min_length=1, max_length=200, pattern=r"\S")


# --- Data Import/Export ---
class ImportData(BaseModel):
    categories: Optional[List] = None
    memories: Optional[List[MemoryCreate]] = None
    memory_suppressions: Optional[List[MemorySuppressionInput]] = None
    bills: List = []
    fitness: List = []
    settings: dict = {}

    @model_validator(mode="after")
    def unique_memory_sources(self):
        if self.memory_suppressions is not None and self.memories is None:
            raise ValueError("包含删除记录的备份必须包含回忆列表")
        keys = [(m.source, m.source_id) for m in self.memories or [] if m.source_id]
        suppressed = [(m.source, m.source_id) for m in self.memory_suppressions or []]
        if len(keys) != len(set(keys)) or len(suppressed) != len(set(suppressed)) or set(keys) & set(suppressed):
            raise ValueError("备份包含重复或冲突的回忆来源")
        return self


# --- Data ---
class ExportData(BaseModel):
    bills: List
    fitness: List
    settings: dict
