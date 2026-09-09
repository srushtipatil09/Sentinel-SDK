import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class NotificationConfigCreate(BaseModel):
    channel_type: str = Field(..., description="Type of channel: slack, discord, webhook, email")
    target_url: Optional[str] = Field(None, max_length=500, description="Webhook URL or HTTP endpoint")
    settings_json: Dict[str, Any] = Field(default_factory=dict, description="Channel specific settings (e.g. email, severity_filter)")
    is_enabled: bool = Field(True, description="Whether channel is actively receiving alerts")


class NotificationConfigUpdate(BaseModel):
    channel_type: Optional[str] = None
    target_url: Optional[str] = None
    settings_json: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None


class NotificationConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    channel_type: str
    target_url: Optional[str] = None
    settings_json: Dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool
    created_at: datetime


class NotificationHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: Optional[uuid.UUID] = None
    channel_type: str
    recipient: str
    status: str
    sent_at: datetime
    error_message: Optional[str] = None


class NotificationTestResponse(BaseModel):
    success: bool
    message: str
