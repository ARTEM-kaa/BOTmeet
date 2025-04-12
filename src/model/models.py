from datetime import datetime
from typing import List

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, ForeignKey, Integer, Numeric,
    String, TIMESTAMP, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.meta import Base


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    firstname: Mapped[str] = mapped_column(String(25), nullable=False)
    lastname: Mapped[str] = mapped_column(String(25), nullable=False)
    mname: Mapped[str] = mapped_column(String(25), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String, nullable=False)
    bio: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    photo: Mapped['Photo'] = relationship('Photo', back_populates='user', uselist=False, cascade='all, delete-orphan')
    preferences: Mapped['Preference'] = relationship('Preference', back_populates='user', uselist=False, cascade='all, delete-orphan')
    ratings_given: Mapped[List['Rating']] = relationship('Rating', foreign_keys='Rating.from_user_id', back_populates='from_user')
    ratings_received: Mapped[List['Rating']] = relationship('Rating', foreign_keys='Rating.to_user_id', back_populates='to_user')
    likes_given: Mapped[List['Like']] = relationship('Like', foreign_keys='Like.from_user_id', back_populates='from_user')
    likes_received: Mapped[List['Like']] = relationship('Like', foreign_keys='Like.to_user_id', back_populates='to_user')
    messages_sent: Mapped[List['Message']] = relationship('Message', foreign_keys='Message.sender_id', back_populates='sender')
    messages_received: Mapped[List['Message']] = relationship('Message', foreign_keys='Message.receiver_id', back_populates='receiver')

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


class Rating(Base):
    __tablename__ = 'ratings'

    id: Mapped[int] = mapped_column(primary_key=True)
    from_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    to_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    from_user: Mapped['User'] = relationship('User', foreign_keys=[from_user_id], back_populates='ratings_given')
    to_user: Mapped['User'] = relationship('User', foreign_keys=[to_user_id], back_populates='ratings_received')

    __table_args__ = (
        UniqueConstraint('from_user_id', 'to_user_id', name='uq_ratings_from_to'),
        CheckConstraint('score >= 0 AND score <= 5', name='ck_ratings_score_range'),
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


class Message(Base):
    __tablename__ = 'messages'

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    receiver_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    content: Mapped[str] = mapped_column(String(2500), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    sender: Mapped['User'] = relationship('User', foreign_keys=[sender_id], back_populates='messages_sent')
    receiver: Mapped['User'] = relationship('User', foreign_keys=[receiver_id], back_populates='messages_received')
