"""Email notifications for Todo Aggregator."""

from .email_sender import send_error_email, send_success_email, send_welcome_email

__all__ = ["send_success_email", "send_error_email", "send_welcome_email"]
