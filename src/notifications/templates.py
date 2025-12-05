"""HTML email templates for Todo Aggregator notifications."""

from datetime import datetime


def get_success_template(
    name: str,
    created: int,
    completed: int,
    slack_count: int,
    gmail_count: int,
    notion_url: str,
) -> tuple[str, str]:
    """Generate success email content.

    Args:
        name: User's display name
        created: Number of new todos created
        completed: Number of todos auto-completed
        slack_count: Number of Slack messages scanned
        gmail_count: Number of Gmail threads scanned
        notion_url: Link to user's Notion database

    Returns:
        Tuple of (subject, html_body)
    """
    date_str = datetime.now().strftime("%b %d, %Y")
    subject = f"✅ Todo Aggregator Summary - {date_str}"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #28a745; margin-bottom: 20px;">✅ Daily Todo Summary</h2>

    <p>Hi {name},</p>

    <p>Your daily todo aggregation is complete!</p>

    <div style="background: #f8f9fa; border-radius: 8px; padding: 16px; margin: 20px 0;">
        <h3 style="margin: 0 0 12px 0; font-size: 14px; color: #666; text-transform: uppercase;">📊 Summary</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #e9ecef;">New todos found</td>
                <td style="padding: 8px 0; border-bottom: 1px solid #e9ecef; text-align: right; font-weight: 600;">{created}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">Todos auto-completed</td>
                <td style="padding: 8px 0; text-align: right; font-weight: 600;">{completed}</td>
            </tr>
        </table>
    </div>

    <div style="background: #f8f9fa; border-radius: 8px; padding: 16px; margin: 20px 0;">
        <h3 style="margin: 0 0 12px 0; font-size: 14px; color: #666; text-transform: uppercase;">📥 Sources Scanned</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #e9ecef;">Slack messages</td>
                <td style="padding: 8px 0; border-bottom: 1px solid #e9ecef; text-align: right; font-weight: 600;">{slack_count}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">Gmail threads</td>
                <td style="padding: 8px 0; text-align: right; font-weight: 600;">{gmail_count}</td>
            </tr>
        </table>
    </div>

    <p style="margin: 24px 0;">
        <a href="{notion_url}" style="display: inline-block; background: #000; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 500;">View Todos in Notion</a>
    </p>

    <hr style="border: none; border-top: 1px solid #e9ecef; margin: 24px 0;">

    <p style="color: #666; font-size: 14px;">— Todo Aggregator</p>
</body>
</html>"""

    return subject, html


def get_error_template(
    name: str,
    error: str,
    registration_url: str,
) -> tuple[str, str]:
    """Generate error email content.

    Args:
        name: User's display name
        error: Error message
        registration_url: Link to re-register

    Returns:
        Tuple of (subject, html_body)
    """
    date_str = datetime.now().strftime("%b %d, %Y")
    subject = f"❌ Todo Aggregator Failed - {date_str}"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #dc3545; margin-bottom: 20px;">❌ Aggregation Failed</h2>

    <p>Hi {name},</p>

    <p>Your todo aggregation failed this morning.</p>

    <div style="background: #fff3f3; border: 1px solid #f5c6cb; border-radius: 8px; padding: 16px; margin: 20px 0;">
        <h3 style="margin: 0 0 8px 0; font-size: 14px; color: #721c24;">Error Details</h3>
        <code style="font-size: 13px; color: #721c24; word-break: break-word;">{error}</code>
    </div>

    <p>This usually means one of your tokens expired. Please update your credentials:</p>

    <p style="margin: 24px 0;">
        <a href="{registration_url}" style="display: inline-block; background: #dc3545; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 500;">Update Credentials</a>
    </p>

    <p style="color: #666;">If you need help, reach out to Clay.</p>

    <hr style="border: none; border-top: 1px solid #e9ecef; margin: 24px 0;">

    <p style="color: #666; font-size: 14px;">— Todo Aggregator</p>
</body>
</html>"""

    return subject, html


def get_welcome_template(
    name: str,
    trigger_url: str,
    notion_url: str,
) -> tuple[str, str]:
    """Generate welcome email content.

    Args:
        name: User's display name
        trigger_url: Personal trigger URL
        notion_url: Link to user's Notion database

    Returns:
        Tuple of (subject, html_body)
    """
    subject = "🎉 Todo Aggregator - You're All Set!"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #28a745; margin-bottom: 20px;">🎉 Welcome to Todo Aggregator!</h2>

    <p>Hi {name},</p>

    <p>Your Todo Aggregator is ready! It will run automatically every day at <strong>7am PT</strong>.</p>

    <div style="background: #f8f9fa; border-radius: 8px; padding: 16px; margin: 20px 0;">
        <h3 style="margin: 0 0 12px 0; font-size: 14px; color: #666; text-transform: uppercase;">🔗 Your Personal Links</h3>
        <p style="margin: 8px 0;"><strong>Run Now:</strong><br>
        <a href="{trigger_url}" style="color: #007bff; word-break: break-all;">{trigger_url}</a></p>
        <p style="margin: 8px 0 0 0;"><strong>Notion Database:</strong><br>
        <a href="{notion_url}" style="color: #007bff; word-break: break-all;">{notion_url}</a></p>
    </div>

    <p>You can bookmark the "Run Now" link to trigger your aggregation anytime.</p>

    <p style="margin: 24px 0;">
        <a href="{trigger_url}" style="display: inline-block; background: #28a745; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 500;">Run Now</a>
    </p>

    <hr style="border: none; border-top: 1px solid #e9ecef; margin: 24px 0;">

    <p style="color: #666; font-size: 14px;">— Todo Aggregator</p>
</body>
</html>"""

    return subject, html
