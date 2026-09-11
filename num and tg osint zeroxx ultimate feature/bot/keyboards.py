from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def help_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🎫 Create Ticket", callback_data="ticket:create")]]
    )


def contact_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💬 Contact User", url=f"tg://user?id={user_id}")]]
    )
