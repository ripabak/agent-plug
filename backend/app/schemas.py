"""Pydantic request/response schemas."""
import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth ---
class UserRegister(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
    created_at: datetime.datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# --- Agents ---
class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    system_prompt: str | None = None
    welcome_message: str = "Hi! How can I help you?"
    theme_color: str = "#4f46e5"
    avatar_emoji: str = "🤖"
    chat_theme: str = ""
    show_thinking: bool = True
    show_tools: bool = True


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    system_prompt: str | None = None
    welcome_message: str | None = None
    theme_color: str | None = None
    avatar_emoji: str | None = None
    chat_theme: str | None = None
    show_thinking: bool | None = None
    show_tools: bool | None = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    description: str
    system_prompt: str | None
    welcome_message: str
    theme_color: str
    avatar_emoji: str
    avatar_url: str | None = None
    avatar_kind: str = "photo"
    chat_theme: str
    show_thinking: bool
    show_tools: bool
    public_token: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AgentPublicConfig(BaseModel):
    """Non-secret agent info exposed to the widget via token auth.

    Includes the chat display config (theme + show thinking/tools toggles) so
    the live widget renders exactly what was configured in the dashboard
    preview — the widget no longer has its own adjustment UI.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    welcome_message: str
    theme_color: str
    avatar_emoji: str
    avatar_url: str | None = None
    avatar_kind: str = "photo"
    chat_theme: str
    show_thinking: bool
    show_tools: bool


class EmbedResponse(BaseModel):
    html: str
    agent_id: int
    public_token: str


# --- Sources (RAG) ---
class SourceCreate(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=50)


class TextSourceCreate(BaseModel):
    """Pasted long-form text knowledge source."""

    title: str = Field(default="Pasted text", min_length=1, max_length=200)
    content: str = Field(min_length=10, max_length=200_000)


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    url: str
    kind: str
    file_name: str | None
    file_size: int | None
    status: str
    title: str | None
    error: str | None
    chunk_count: int
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ReindexRequest(BaseModel):
    only_failed: bool = False


# --- Chat ---
class ChatMessage(BaseModel):
    """One chat message sent by the client to run.start."""

    role: str = Field(pattern="^(user|assistant|human|ai)$")
    content: str


class RunStartInput(BaseModel):
    """input payload for the run.start command."""

    agent_id: int | None = None
    messages: list[ChatMessage] = []
    thread_id: str | None = None  # public widget: optional custom thread id


class CommandResponse(BaseModel):
    type: str
    id: str | None = None
    result: dict | None = None
    error: str | None = None
    message: str | None = None


# --- Usage (dashboard tab) ---
class UsageLog(BaseModel):
    """One chat request row in the usage history list."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    channel: str
    thread_id: str
    model: str | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float | None
    country: str | None
    status: str
    created_at: datetime.datetime


class UsagePoint(BaseModel):
    """One day in the usage time series (zero-filled for empty days)."""

    date: str
    requests: int
    input_tokens: int
    output_tokens: int


class UsageCountry(BaseModel):
    """Requests grouped by client country (ISO alpha-2 code)."""

    country: str
    requests: int


class UsageSummary(BaseModel):
    """Totals + daily series backing the two usage charts."""

    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    series: list[UsagePoint]
    countries: list[UsageCountry]


class UsageResponse(BaseModel):
    """Full payload for the Usage tab: charts data + paginated history."""

    summary: UsageSummary
    items: list[UsageLog]
    total: int
    page: int
    page_size: int
    pages: int
