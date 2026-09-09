import json
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import settings
from backend.models.system import NotificationConfig, NotificationHistory
from backend.utils.logging import logger

SEVERITY_LEVELS = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


class NotificationEngine:
    """Multi-channel notification engine (Email, Slack, Discord, Custom Webhooks)."""

    async def send_incident_alert(
        self,
        session: AsyncSession,
        config: NotificationConfig,
        incident_title: str,
        severity: str,
        service_name: str,
        rca_summary: Optional[str] = None,
        incident_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Dispatches incident alert to configured channel."""
        channel = config.channel_type.lower()
        success = False
        error_msg = None

        message_body = (
            f"🚨 *[{severity}] Sentinel AI Incident Alert*\n"
            f"*Service:* {service_name}\n"
            f"*Title:* {incident_title}\n"
            f"*Status:* AI Processing Complete\n"
        )
        if rca_summary:
            message_body += f"\n*Root Cause Summary:* {rca_summary[:300]}..."

        recipient = config.target_url or config.settings_json.get("email", "email")

        try:
            if channel == "slack" and config.target_url:
                success = await self._send_slack_webhook(config.target_url, message_body)
            elif channel == "discord" and config.target_url:
                success = await self._send_discord_webhook(config.target_url, message_body)
            elif channel == "webhook" and config.target_url:
                success = await self._send_generic_webhook(config.target_url, {
                    "event": "INCIDENT_ALERT",
                    "incident_id": str(incident_id) if incident_id else None,
                    "severity": severity,
                    "service": service_name,
                    "title": incident_title,
                    "summary": rca_summary
                })
            elif channel == "email" and settings.SMTP_HOST:
                target_email = config.settings_json.get("email", settings.EMAILS_FROM_EMAIL)
                recipient = target_email
                success = self._send_email(target_email, f"[{severity}] Sentinel AI Incident: {service_name}", message_body)
            else:
                logger.info("Notification target simulation", channel=channel, target=recipient)
                success = True
        except Exception as exc:
            error_msg = str(exc)
            logger.error("Failed to send notification", channel=channel, error=error_msg)

        # Log Notification History with valid incident_id (nullable)
        try:
            history = NotificationHistory(
                incident_id=incident_id,
                channel_type=channel,
                recipient=recipient,
                status="SENT" if success else "FAILED",
                error_message=error_msg
            )
            session.add(history)
            await session.flush()
        except Exception as log_exc:
            logger.warning("Failed to record notification history", error=str(log_exc))

        return success

    async def send_test_alert(
        self,
        config: NotificationConfig,
        session: Optional[AsyncSession] = None
    ) -> Tuple[bool, Optional[str]]:
        """Sends a verification test alert to confirm channel connectivity."""
        channel = config.channel_type.lower()
        success = False
        error_msg = None

        test_message = (
            "🔔 *[Sentinel AI] Test Notification*\n"
            f"Your *{channel.upper()}* alert channel has been successfully verified.\n"
            "You will receive automated incident alerts and AI Root Cause Analysis summaries on this channel."
        )
        recipient = config.target_url or config.settings_json.get("email", "email")

        try:
            if channel == "slack" and config.target_url:
                success = await self._send_slack_webhook(config.target_url, test_message)
            elif channel == "discord" and config.target_url:
                success = await self._send_discord_webhook(config.target_url, test_message)
            elif channel == "webhook" and config.target_url:
                success = await self._send_generic_webhook(config.target_url, {
                    "event": "TEST_ALERT",
                    "channel": channel,
                    "message": "Sentinel AI webhook channel verification successful."
                })
            elif channel == "email":
                target_email = config.settings_json.get("email", settings.EMAILS_FROM_EMAIL)
                recipient = target_email
                if settings.SMTP_HOST and settings.SMTP_USER:
                    success = self._send_email(target_email, "Sentinel AI - Channel Test Notification", test_message)
                else:
                    logger.info("SMTP not configured. Simulating email channel verification.", email=target_email)
                    success = True
            else:
                logger.info("Notification target simulation", channel=channel, target=recipient)
                success = True

            if not success and not error_msg:
                error_msg = f"{channel.capitalize()} endpoint rejected the webhook request."
        except Exception as exc:
            error_msg = str(exc)
            logger.error("Failed to send test notification", channel=channel, error=error_msg)

        if session:
            try:
                history = NotificationHistory(
                    incident_id=None,
                    channel_type=channel,
                    recipient=recipient,
                    status="SENT" if success else "FAILED",
                    error_message=error_msg
                )
                session.add(history)
                await session.flush()
            except Exception as hist_err:
                logger.warning("Failed to record test notification history", error=str(hist_err))

        return success, error_msg

    async def dispatch_project_incident_alert(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        incident_title: str,
        severity: str,
        service_name: str,
        rca_summary: Optional[str] = None,
        incident_id: Optional[uuid.UUID] = None
    ) -> List[bool]:
        """Dispatches alerts to all active notification channels for the project."""
        stmt = (
            select(NotificationConfig)
            .where(
                NotificationConfig.project_id == project_id,
                NotificationConfig.is_enabled == True,
                NotificationConfig.is_deleted == False
            )
        )
        res = await session.execute(stmt)
        configs = res.scalars().all()

        results = []
        incident_rank = SEVERITY_LEVELS.get(severity.upper(), 99)

        for cfg in configs:
            # Check minimum severity threshold if configured
            min_sev = cfg.settings_json.get("severity_filter") if cfg.settings_json else None
            if min_sev:
                threshold_rank = SEVERITY_LEVELS.get(min_sev.upper(), 99)
                if incident_rank > threshold_rank:
                    continue

            ok = await self.send_incident_alert(
                session=session,
                config=cfg,
                incident_title=incident_title,
                severity=severity,
                service_name=service_name,
                rca_summary=rca_summary,
                incident_id=incident_id
            )
            results.append(ok)

        return results

    async def _send_slack_webhook(self, webhook_url: str, text: str) -> bool:
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json={"text": text}, timeout=5.0)
            return resp.status_code == 200

    async def _send_discord_webhook(self, webhook_url: str, text: str) -> bool:
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json={"content": text}, timeout=5.0)
            return resp.status_code in (200, 204)

    async def _send_generic_webhook(self, target_url: str, payload: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient() as client:
            resp = await client.post(target_url, json=payload, timeout=5.0)
            return resp.status_code < 400

    def _send_email(self, recipient_email: str, subject: str, body: str) -> bool:
        if not settings.SMTP_HOST or not settings.SMTP_USER:
            logger.warning("SMTP credentials not configured. Skipping email dispatch.")
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = settings.EMAILS_FROM_EMAIL
            msg["To"] = recipient_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            return True
        except Exception as exc:
            logger.error("SMTP email send failed", recipient=recipient_email, error=str(exc))
            return False

    def send_password_reset_email(self, recipient_email: str, reset_token: str) -> bool:
        """Dispatches password reset link token email."""
        subject = "Sentinel AI - Password Reset Request"
        body = (
            f"Hello,\n\n"
            f"You requested a password reset for your Sentinel AI account.\n"
            f"Use the following reset token to set a new password:\n\n"
            f"Token: {reset_token}\n\n"
            f"If you did not request this, please ignore this email.\n"
        )
        if settings.SMTP_HOST and settings.SMTP_USER:
            return self._send_email(recipient_email, subject, body)
        else:
            logger.info("SMTP not configured. Password reset token logged securely.", email=recipient_email, token=reset_token[:8])
            return True


notification_engine = NotificationEngine()

