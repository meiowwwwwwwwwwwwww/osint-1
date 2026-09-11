"""All bot handlers, shared by polling and webhook entrypoints."""

from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from datetime import datetime
import html
import logging
import re
import secrets
import time
from typing import Any

from aiogram import BaseMiddleware, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot import Settings
from bot.api_client import (
    NumberApiClient,
    NumberApiConnectionError,
    NumberApiError,
    NumberApiHttpError,
    NumberApiResponseError,
    NumberApiTimeoutError,
    TelegramApiClient,
)
from bot import keyboards, messages
from bot.recipients import add_recipient, get_recipients

logger = logging.getLogger(__name__)
router = Router()
_last_lookup: dict[int, float] = {}
_observed_users: dict[int, float] = {}
_audit_api_response: ContextVar[str | None] = ContextVar("audit_api_response", default=None)

_NUMBER_PATTERN = re.compile(r"^[0-9]{7,15}$")
_TELEGRAM_USER_ID_PATTERN = re.compile(r"^[1-9][0-9]{0,14}$")
_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "country": ("country", "country_name"),
    "region": ("region", "state"),
    "carrier": ("carrier", "operator"),
    "type": ("type", "number_type"),
    "valid": ("valid", "is_valid", "validity"),
    "line_type": ("line_type",),
    "location": ("location",),
}


class UserActivityMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[..., Awaitable[Any]], event: Any, data: dict[str, Any]) -> Any:
        user = getattr(event, "from_user", None)
        if user:
            _observed_users[user.id] = time.monotonic()
            add_recipient(user.id)
        token = _audit_api_response.set(None)
        try:
            return await handler(event, data)
        finally:
            api_response = _audit_api_response.get()
            _audit_api_response.reset(token)
            settings = data.get("settings")
            if isinstance(event, Message) and user and isinstance(settings, Settings):
                await _send_audit_log(event, settings, api_response)


async def _send_audit_log(message: Message, settings: Settings, api_response: str | None) -> None:
    if not settings.alt_tg_id or not message.from_user:
        return
    user = message.from_user
    username = f"@{user.username}" if user.username else "Not set"
    display_name = " ".join(part for part in (user.first_name, user.last_name) if part).strip() or "Unknown"
    message_text = message.text or message.caption or f"[{message.content_type}]"
    now = datetime.now().astimezone()
    try:
        await message.bot.send_message(
            settings.alt_tg_id,
            messages.audit_log(
                {
                    "name": html.escape(display_name),
                    "id": str(user.id),
                    "username": html.escape(username),
                },
                html.escape(message_text),
                now.strftime("%d %B %Y"),
                now.strftime("%I:%M %p"),
                api_response,
            ),
        )
    except Exception:
        logger.exception("Could not send audit log")


def _is_admin(user_id: int, settings: Settings) -> bool:
    return user_id == settings.admin_id


def _number_from_message(message: Message) -> str | None:
    text = message.text or ""
    parts = text.split(maxsplit=1)
    candidate = parts[1].strip() if len(parts) == 2 else ""
    return candidate if _NUMBER_PATTERN.fullmatch(candidate) else None


def _telegram_user_id_from_message(message: Message) -> str | None:
    text = message.text or ""
    parts = text.split(maxsplit=1)
    candidate = parts[1].strip() if len(parts) == 2 else ""
    return candidate if _TELEGRAM_USER_ID_PATTERN.fullmatch(candidate) else None


def _display_fields(payload: dict[str, Any]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for output_key, aliases in _FIELD_ALIASES.items():
        for alias in aliases:
            value = payload.get(alias)
            if value is not None and not isinstance(value, (dict, list)):
                if isinstance(value, bool):
                    text = "Yes" if value else "No"
                else:
                    text = str(value).strip()
                if text:
                    fields[output_key] = html.escape(text)
                    break
    return fields


def _api_result_text(payload: Any) -> str | None:
    """Make arbitrary API output readable without returning raw JSON to Telegram."""
    if isinstance(payload, str):
        text = payload.strip()
        return html.escape(text) if text else None
    if isinstance(payload, (int, float, bool)):
        return html.escape(str(payload))
    if isinstance(payload, list):
        if not payload:
            return "No results found."
        entries = [_api_result_text(item) for item in payload[:10]]
        text = "\n\n".join(entry for entry in entries if entry)
        return text or None
    if isinstance(payload, dict):
        entries: list[str] = []
        for key, value in payload.items():
            if value is None:
                continue
            if isinstance(value, (dict, list)):
                rendered = _api_result_text(value)
            elif isinstance(value, bool):
                rendered = "Yes" if value else "No"
            else:
                rendered = str(value).strip()
            if rendered:
                entries.append(f"<b>{html.escape(str(key).replace('_', ' ').title())}:</b> {html.escape(rendered) if not isinstance(value, (dict, list)) else rendered}")
        return "\n".join(entries) or None
    return None


def create_dispatcher(settings: Settings) -> Dispatcher:
    dispatcher = Dispatcher()
    router.message.middleware(UserActivityMiddleware())
    router.callback_query.middleware(UserActivityMiddleware())
    dispatcher.include_router(router)
    return dispatcher


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    user = message.from_user
    await message.answer(messages.home(html.escape(user.first_name or "there"), user.username))


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(messages.HELP, reply_markup=keyboards.help_keyboard())


@router.callback_query(F.data == "ticket:create")
async def create_ticket_handler(callback: CallbackQuery, settings: Settings) -> None:
    if not callback.from_user or not callback.message:
        return
    try:
        ticket = {
            "ticket_id": secrets.randbelow(90000) + 10000,
            "telegram_user_id": callback.from_user.id,
            "username": callback.from_user.username,
            "first_name": html.escape(callback.from_user.first_name or "Unknown"),
            "created_at": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        }
        await callback.bot.send_message(
            settings.admin_id,
            messages.ticket_alert({**ticket, "username": html.escape(ticket["username"]) if ticket["username"] else None}),
            reply_markup=keyboards.contact_keyboard(callback.from_user.id),
        )
        await callback.answer("Ticket sent to support")
        await callback.message.answer(messages.TICKET_CREATED.format(ticket_id=ticket["ticket_id"]))
    except Exception:
        logger.exception("Could not create support ticket")
        await callback.answer("Ticket creation is temporarily unavailable", show_alert=True)


@router.message(Command("num"))
async def number_handler(message: Message, api_client: NumberApiClient, settings: Settings) -> None:
    number = _number_from_message(message)
    if not number:
        await message.answer(messages.INVALID_NUMBER)
        return
    user_id = message.from_user.id
    now = time.monotonic()
    if now - _last_lookup.get(user_id, 0) < settings.num_rate_limit_seconds:
        await message.answer(messages.RATE_LIMITED)
        return
    _last_lookup[user_id] = now
    try:
        response = await api_client.lookup(number)
        _audit_api_response.set(_api_result_text(response.payload))
        if response.is_json and isinstance(response.payload, dict):
            fields = _display_fields(response.payload)
            if fields:
                await message.answer(messages.format_lookup(number, fields))
                return
            result_text = _api_result_text(response.payload)
        else:
            result_text = _api_result_text(response.payload)
        if not result_text:
            await message.answer(messages.NO_METADATA)
            return
        await message.answer(messages.format_api_result(number, result_text))
    except NumberApiTimeoutError:
        await message.answer(messages.LOOKUP_TIMEOUT)
    except NumberApiConnectionError:
        await message.answer(messages.LOOKUP_CONNECTION_ERROR)
    except NumberApiHttpError:
        await message.answer(messages.LOOKUP_HTTP_ERROR)
    except NumberApiResponseError:
        await message.answer(messages.LOOKUP_RESPONSE_ERROR)
    except NumberApiError:
        await message.answer(messages.LOOKUP_ERROR)


@router.message(Command("tg"))
async def telegram_user_handler(message: Message, telegram_api_client: TelegramApiClient, settings: Settings) -> None:
    telegram_user_id = _telegram_user_id_from_message(message)
    if not telegram_user_id:
        await message.answer(messages.INVALID_TELEGRAM_USER_ID)
        return
    user_id = message.from_user.id
    now = time.monotonic()
    if now - _last_lookup.get(user_id, 0) < settings.num_rate_limit_seconds:
        await message.answer(messages.RATE_LIMITED)
        return
    _last_lookup[user_id] = now
    try:
        response = await telegram_api_client.lookup(telegram_user_id)
        result_text = _api_result_text(response.payload)
        _audit_api_response.set(result_text)
        if not result_text:
            await message.answer(messages.TELEGRAM_LOOKUP_NO_RESULT)
            return
        await message.answer(messages.format_telegram_lookup(telegram_user_id, result_text))
    except NumberApiTimeoutError:
        await message.answer(messages.LOOKUP_TIMEOUT)
    except NumberApiConnectionError:
        await message.answer(messages.LOOKUP_CONNECTION_ERROR)
    except NumberApiHttpError:
        await message.answer(messages.LOOKUP_HTTP_ERROR)
    except NumberApiResponseError:
        await message.answer(messages.LOOKUP_RESPONSE_ERROR)
    except NumberApiError:
        await message.answer(messages.LOOKUP_ERROR)
    except Exception:
        logger.exception("Unexpected Telegram user lookup failure")
        await message.answer(messages.LOOKUP_ERROR)


@router.message(Command("stat"))
async def stat_handler(message: Message, settings: Settings) -> None:
    if not _is_admin(message.from_user.id, settings):
        await message.answer("⛔ This command is available to administrators only.")
        return
    cutoff = time.monotonic() - (settings.active_hours * 3600)
    active = sum(last_seen >= cutoff for last_seen in _observed_users.values())
    await message.answer(messages.stats(len(_observed_users), active, settings.active_hours))


@router.message(Command("broadcast"))
async def broadcast_handler(message: Message, settings: Settings) -> None:
    if not _is_admin(message.from_user.id, settings):
        await message.answer("⛔ This command is available to administrators only.")
        return
    parts = (message.text or "").split(maxsplit=1)
    content = parts[1].strip() if len(parts) == 2 else ""
    if not content:
        await message.answer(messages.BROADCAST_INVALID)
        return
    successful = 0
    failed = 0
    for recipient_id in get_recipients():
        try:
            await message.bot.send_message(recipient_id, messages.broadcast(content))
            successful += 1
        except Exception:
            failed += 1
            logger.warning("Could not deliver broadcast to %s", recipient_id, exc_info=True)
    await message.answer(messages.broadcast_result(successful, failed))


def build_services(settings: Settings) -> tuple[NumberApiClient, TelegramApiClient]:
    return NumberApiClient(settings), TelegramApiClient(settings)
