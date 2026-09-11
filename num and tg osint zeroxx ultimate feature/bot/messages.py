"""User-facing message templates."""

import html

FOOTER = "🛠️ Developer — @Brutoixx / @Esahekya"
SEPARATOR = "━━━━━━━━━━━━━━━━"


def home(first_name: str, username: str | None) -> str:
    account = f"@{username}" if username else "Not set"
    return (
        f"👋 <b>Welcome, {first_name}!</b>\n\n"
        f"👤 Username: {account}\n\n"
        "🔎 This bot checks a phone number through the configured lookup service "
        "and displays only the metadata returned by that service.\n\n"
        f"{SEPARATOR}\n"
        "📚 <b>Available Commands</b>\n"
        "• /help — How the bot works\n"
        "• /num — Look up a number\n\n"
        "• /tg — Telegram User ID lookup\n\n"
        "📝 <b>Note:</b> Enter number without +91\n\n"
        f"{FOOTER}"
    )


HELP = (
    "🆘 <b>Help & Support</b>\n\n"
    f"{SEPARATOR}\n"
    "• /start — Open the home screen\n"
    "• /num 1234567890 — Look up a number\n\n"
    "• /tg 7290081245 — Telegram User ID lookup\n\n"
    "Enter digits without <code>+91</code>. The bot shows only metadata "
    "provided by the configured service.\n\n"
    "Need assistance? Create a support ticket below.\n\n"
    f"{FOOTER}"
)

INVALID_NUMBER = (
    "❌ <b>Invalid number</b>\n\n"
    "Usage:\n<code>/num 1234567890</code>\n\n"
    "📝 Enter the number without +91."
)
INVALID_TELEGRAM_USER_ID = "❌ Wrong input. Usage: /tg 7290081245"

RATE_LIMITED = "⏳ Please wait a few seconds before requesting another lookup."
LOOKUP_ERROR = "⚠️ The lookup service is temporarily unavailable. Please try again later."
LOOKUP_TIMEOUT = "⏳ The lookup service timed out. Please try again shortly."
LOOKUP_CONNECTION_ERROR = "⚠️ The lookup service could not be reached. Please try again later."
LOOKUP_HTTP_ERROR = "⚠️ The lookup service returned an error. Please try again later."
LOOKUP_RESPONSE_ERROR = "⚠️ The lookup service returned an invalid response. Please try again later."
NO_METADATA = "ℹ️ The lookup service returned no displayable metadata for this number."
TELEGRAM_LOOKUP_NO_RESULT = "ℹ️ No Telegram user details were returned for this ID."
TICKET_CREATED = (
    "🎫 <b>Support Ticket Created</b>\n\n"
    "Your request has been sent to support.\n\n"
    "Ticket ID: <code>#{ticket_id}</code>\n\n"
    "Our support team has been notified.\n\n"
    f"{FOOTER}"
)


def ticket_alert(ticket: dict) -> str:
    username = f"@{ticket['username']}" if ticket.get("username") else "Not set"
    return (
        "🎫 <b>NEW SUPPORT TICKET</b>\n"
        f"{SEPARATOR}\n"
        f"🎟 Ticket ID: <code>#{ticket['ticket_id']}</code>\n"
        f"👤 Name: {ticket['first_name']}\n"
        f"🔹 Username: {username}\n"
        f"🆔 User ID: <code>{ticket['telegram_user_id']}</code>\n"
        f"🕒 Date/Time: {ticket['created_at']}\n"
        "📌 Status: Open\n"
        f"{SEPARATOR}"
    )


def stats(total: int, active: int, active_hours: int) -> str:
    return (
        "📊 <b>CURRENT INSTANCE STATISTICS</b>\n\n"
        f"👥 Observed since this process started: <b>{total}</b>\n"
        f"🟢 Active in the last {active_hours} hours: <b>{active}</b>\n\n"
        "ℹ️ These are temporary in-memory figures and reset when the process restarts."
    )


BROADCAST_INVALID = "❌ Wrong input. Usage: /broadcast <message>"


def audit_log(user: dict[str, str], message_text: str, date: str, time: str, api_response: str | None) -> str:
    lines = [
        "🔔 <b>Audit Log</b>",
        "",
        f"👤 <b>User:</b> {user['name']}",
        f"🆔 <b>ID:</b> <code>{user['id']}</code>",
        f"🏷️ <b>Username:</b> {user['username']}",
        "",
        f"💬 <b>Message:</b> {message_text}",
        "",
        f"📅 <b>Date:</b> {date}",
        f"🕐 <b>Time:</b> {time}",
    ]
    if api_response:
        lines.extend(["", "🔎 <b>API Response:</b>", api_response])
    lines.extend(["", SEPARATOR, FOOTER])
    return "\n".join(lines)


def broadcast(content: str) -> str:
    return "\n".join(["📢 <b>Broadcast Message</b>", "", html.escape(content), "", SEPARATOR, FOOTER])


def broadcast_result(successful: int, failed: int) -> str:
    return f"📢 Broadcast completed.\n✅ Successful: {successful}\n❌ Failed: {failed}"


def format_lookup(number: str, fields: dict[str, str]) -> str:
    labels = {
        "country": "🌍 Country",
        "region": "📍 Region",
        "carrier": "📡 Carrier",
        "type": "📞 Type",
        "valid": "✅ Valid",
        "line_type": "📞 Line type",
        "location": "📍 Location",
    }
    lines = ["🔎 <b>NUMBER LOOKUP</b>", SEPARATOR, f"📱 Number: <code>{number}</code>"]
    for key, label in labels.items():
        if key in fields:
            lines.append(f"{label}: {fields[key]}")
    lines.extend(["", SEPARATOR, FOOTER])
    return "\n".join(lines)


def format_api_result(number: str, result: str) -> str:
    """Wrap pre-escaped, human-readable API output in the bot's usual layout."""
    return "\n".join([
        "🔎 <b>NUMBER LOOKUP</b>",
        SEPARATOR,
        f"📱 Number: <code>{number}</code>",
        "",
        result,
        "",
        SEPARATOR,
        FOOTER,
    ])


def format_telegram_lookup(telegram_user_id: str, result: str) -> str:
    """Wrap pre-escaped, human-readable Telegram lookup output."""
    return "\n".join([
        "🔍 <b>Telegram User ID Details</b>",
        SEPARATOR,
        f"👤 User ID: <code>{telegram_user_id}</code>",
        "",
        result,
        "",
        SEPARATOR,
        FOOTER,
    ])
