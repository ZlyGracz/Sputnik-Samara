"""Pydantic-схемы. Зеркало components/schemas из docs/openapi.yaml."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator, model_validator

Role = Literal["user", "creator", "admin"]
Str = lambda **kw: Annotated[str, StringConstraints(strip_whitespace=True, **kw)]  # noqa: E731


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel):
    total: int
    limit: int
    offset: int


# ---- auth / users
class RegisterRequest(BaseModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=72)
    full_name: Str(min_length=2, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class User(ORM):
    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: User


class UserBrief(ORM):
    id: int
    full_name: str


class UserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _not_empty(self):
        if not self.model_fields_set:
            raise ValueError("Нужно передать role или is_active")
        if self.role is None and self.is_active is None:
            raise ValueError("role и is_active не могут быть null")
        return self


class UserPage(Page):
    items: list[User]


# ---- courses
class Course(BaseModel):
    id: int
    title: str
    description: str
    cover_media_id: UUID | None
    cover_url: str | None
    is_published: bool
    author: UserBrief
    questions_count: int
    created_at: datetime
    updated_at: datetime


class CoursePage(Page):
    items: list[Course]


class CourseCreate(BaseModel):
    title: Str(min_length=3, max_length=200)
    description: str = Field("", max_length=5000)
    cover_media_id: UUID | None = None


class CourseUpdate(BaseModel):
    title: Str(min_length=3, max_length=200) | None = None
    description: str | None = Field(None, max_length=5000)
    cover_media_id: UUID | None = None
    is_published: bool | None = None

    @model_validator(mode="after")
    def _not_empty(self):
        if not self.model_fields_set:
            raise ValueError("Нужно передать хотя бы одно поле")
        for f in ("title", "description", "is_published"):  # эти поля не nullable
            if f in self.model_fields_set and getattr(self, f) is None:
                raise ValueError(f"{f} не может быть null")
        return self


# ---- questions
class OptionInput(BaseModel):
    text: Str(min_length=1, max_length=300)
    is_correct: bool


class Option(ORM):
    id: int
    text: str
    is_correct: bool


class QuestionInput(BaseModel):
    text: Str(min_length=1, max_length=1000)
    image_media_id: UUID | None = None
    audio_media_id: UUID | None = None
    position: int | None = Field(None, ge=1)
    options: list[OptionInput] = Field(min_length=4, max_length=4)

    @field_validator("options")
    @classmethod
    def _one_correct(cls, v):
        if sum(o.is_correct for o in v) != 1:
            raise ValueError("Ровно один вариант должен быть правильным")
        return v


class Question(BaseModel):
    id: int
    course_id: int
    position: int
    text: str
    image_media_id: UUID | None
    image_url: str | None
    audio_media_id: UUID | None
    audio_url: str | None
    options: list[Option]


class QuestionStat(BaseModel):
    question_id: int
    text: str
    answers_count: int
    correct_rate: float


class CourseStats(BaseModel):
    course_id: int
    attempts_count: int
    finished_count: int
    average_percent: float
    questions: list[QuestionStat]


# ---- attempts
class AttemptOption(ORM):
    id: int
    text: str


class AttemptQuestion(BaseModel):
    id: int
    position: int
    text: str
    image_url: str | None
    audio_url: str | None
    options: list[AttemptOption]
    selected_option_id: int | None
    is_correct: bool | None
    correct_option_id: int | None


class AttemptDetail(BaseModel):
    id: int
    course_id: int
    course_title: str
    status: Literal["in_progress", "finished"]
    started_at: datetime
    finished_at: datetime | None
    total_questions: int
    answered_count: int
    score: int | None
    percent: float | None
    questions: list[AttemptQuestion]


class AttemptSummary(BaseModel):
    id: int
    course_id: int
    course_title: str
    status: Literal["in_progress", "finished"]
    started_at: datetime
    finished_at: datetime | None
    total_questions: int
    score: int | None
    percent: float | None


class AttemptPage(Page):
    items: list[AttemptSummary]


class AnswerRequest(BaseModel):
    question_id: int
    option_id: int


class AnswerResult(BaseModel):
    question_id: int
    selected_option_id: int
    is_correct: bool
    correct_option_id: int
