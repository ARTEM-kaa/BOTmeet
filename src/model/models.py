from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, ForeignKey, Integer, Numeric,
    String, TIMESTAMP, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.model.meta import Base


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    tg_username: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    firstname: Mapped[str] = mapped_column(String(25), nullable=False)
    lastname: Mapped[str] = mapped_column(String(25), nullable=False)
    mname: Mapped[str] = mapped_column(String(25), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String, nullable=False)
    bio: Mapped[str] = mapped_column(String(200), nullable=False)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=2.5)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    dislike_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    photo: Mapped['Photo'] = relationship('Photo', back_populates='user', uselist=False, cascade='all, delete-orphan')
    preferences: Mapped['Preference'] = relationship('Preference', back_populates='user', uselist=False, cascade='all, delete-orphan')
    likes_given: Mapped[List['Like']] = relationship('Like', foreign_keys='Like.from_user_id', back_populates='from_user')
    likes_received: Mapped[List['Like']] = relationship('Like', foreign_keys='Like.to_user_id', back_populates='to_user')

    __table_args__ = (
        CheckConstraint('age BETWEEN 10 AND 110', name='ck_users_age_range'),
    )


class Photo(Base):
    __tablename__ = 'photos'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    added_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    user: Mapped['User'] = relationship('User', back_populates='photo')


class Preference(Base):
    __tablename__ = 'preferences'

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    preferred_gender: Mapped[str]
    min_age: Mapped[int]
    max_age: Mapped[int]
    min_rating: Mapped[float] = mapped_column(Numeric(2, 1))
    max_rating: Mapped[float] = mapped_column(Numeric(2, 1))

    user: Mapped['User'] = relationship('User', back_populates='preferences')

    __table_args__ = (
        CheckConstraint('min_age >= 10', name='ck_preferences_min_age'),
        CheckConstraint('max_age <= 110', name='ck_preferences_max_age'),
        CheckConstraint('min_rating >= 0 AND min_rating <= 5', name='ck_preferences_min_rating'),
        CheckConstraint('max_rating >= 0 AND max_rating <= 5', name='ck_preferences_max_rating'),
    )


class Like(Base):
    __tablename__ = 'likes'

    from_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    to_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    is_like: Mapped[bool] = mapped_column(Boolean, default=True)
    liked_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    from_user: Mapped['User'] = relationship('User', foreign_keys=[from_user_id], back_populates='likes_given')
    to_user: Mapped['User'] = relationship('User', foreign_keys=[to_user_id], back_populates='likes_received')


class Match(Base):
    __tablename__ = 'matches'

    id: Mapped[int] = mapped_column(primary_key=True)
    user1_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    user2_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    matched_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user1_id', 'user2_id', name='uq_matches_user1_user2'),
    )
