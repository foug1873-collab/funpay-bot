import logging
import uuid
import asyncio
import nest_asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Применяем patch для async-цикла на хостинге
try:
    nest_asyncio.apply()
except Exception:
    pass

logging.basicConfig(level=logging.INFO)

TOKEN = "8845028227:AAHZxXu-uEVHBUAkprM_qtqkkzDauhPjJVM"
WELCOME_GIF_ID = "CgACAgIAAxkBAAIBDmqYRON9IlKYI-x4V2S5E8gCfOLbAAKRogAC7ldhS5Ms_Sf7yK8VPQQ"

CURRENCY, AMOUNT, DESCRIPTION, PARTNER = range(4)

STATUS_NAMES = {
    "created": "🔵 Ожидает подключения покупателя",
    "accepted": "🟢 Ожидает оплаты покупателем",
    "paid": "🟡 Оплачена (ожидает товар)",
    "item_transferred": "🟠 Товар передан (на проверке)",
    "completed": "🟣 Завершена",
    "rejected": "🔴 Отклонена",
}

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤝 Создать сделку", callback_data="create_deal")],
        [InlineKeyboardButton("📦 Мои сделки", callback_data="my_deals"), InlineKeyboardButton("💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton("📖 Принцип работы", callback_data="how_it_works"), InlineKeyboardButton("☎️ Поддержка", callback_data="support")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0].startswith("deal_"):
        deal_id = context.args[0].replace("deal_", "")
        user = update.effective_user
        if user:
            context.user_data["joining_deal_id"] = deal_id
            await update.message.reply_text(
                f"🤝 Вы хотите присоединиться к сделке #{deal_id} в качестве покупателя.\n\n"
                f"Нажмите кнопку ниже, чтобы подтвердить участие:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Подтвердить и войти в сделку", callback_data=f"join_deal_{deal_id}")]
                ])
            )
            return

    user = update.effective_user
    name = user.first_name if user else "Пользователь"
    
    caption = (
        f"👋 Привет, <b>{name}</b>!\n\n"
        "Добро пожаловать в безопасную среду <b>P2P-гаранта</b>.\n\n"
        "🛡 Мы помогаем безопасно проводить сделки по продаже игровых ценностей, аккаунтов, "
        "валюты и других цифровых товаров.\n\n"
        "Выберите нужное действие в меню ниже:"
    )
    
    try:
        await update.message.reply_animation(
            animation=WELCOME_GIF_ID,
            caption=caption,
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    except Exception:
        await update.message.reply_text(
            text=caption,
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )

async def how_it_works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "📖 <b>Как работает P2P-Гарант:</b>\n\n"
        "1️⃣ <b>Создание сделки:</b> Продавец создает сделку, указывает валюту, сумму и описание товара. Бот генерирует уникальную ссылку-приглашение.\n"
        "2️⃣ <b>Присоединение покупателя:</b> Продавец отправляет ссылку покупателю. Покупатель переходит по ней и подтверждает участие.\n"
        "3️⃣ <b>Оплата:</b> Покупатель переводит средства. Деньги надежно резервируются на счете гаранта.\n"
        "4️⃣ <b>Передача товара:</b> Продавец передает данные или товар покупателю.\n"
        "5️⃣ <b>Завершение:</b> Покупатель проверяет товар и подтверждает получение. Средства автоматически зачисляются продавцу."
    )
    
    await query.edit_message_caption(
        caption=text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад в меню", callback_data="main_menu")]])
    )

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "🛡 Главное меню P2P-гаранта. Выберите действие:"
    try:
        await query.edit_message_caption(
            caption=text,
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    except Exception:
        await query.edit_message_text(
            text=text,
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )

async def not_implemented(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Этот раздел в разработке.")

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(how_it_works, pattern="^how_it_works$"))
    application.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(not_implemented, pattern="^(create_deal|my_deals|balance|support)$"))

    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
    
