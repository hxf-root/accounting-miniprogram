import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Bill(Base):
    __tablename__ = "bills"
    __table_args__ = (
        Index("ix_bills_user_date", "user_id", "date"),
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    type = Column(String(10), nullable=False)  # expense / income
    amount = Column(Float, nullable=False)
    category_id = Column(Integer, nullable=False)
    category_name = Column(String(50), nullable=False)
    payment_method = Column(String(20), default="wechat")
    remark = Column(Text, default="")
    date = Column(String(10), nullable=False)  # 2026-06-15
    time = Column(String(5), nullable=False)   # 12:30
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        Index("ix_categories_user_type", "user_id", "type"),
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    type = Column(String(10), nullable=False)  # expense / income
    name = Column(String(50), nullable=False)
    icon = Column(String(10), default="📦")
    color = Column(String(20), default="#5cb8a0")
    is_custom = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)


class FitnessRecord(Base):
    __tablename__ = "fitness_records"
    __table_args__ = (
        Index("ix_fitness_user_date", "user_id", "date"),
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    exercise_type = Column(String(50), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    calories = Column(Integer, default=0)
    date = Column(String(10), nullable=False)
    time = Column(String(5), nullable=False)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Settings(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True, nullable=False)
    monthly_budget = Column(Float, default=0)
    fitness_daily_goal_minutes = Column(Integer, default=30)
    fitness_daily_goal_calories = Column(Integer, default=300)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
