import logging
import uuid
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

try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)

TOKEN = "8845028227:AAHZxXu-uEVHBUAkprM_qtqkkzDauhPjJVM"

# Рабочий file_id гифки
WELCOME_GIF_ID = "CgACAgIAAxkBAAIBDmqYRON9IlKYI-x4V2S5E8gCfOLbAAKRogAC7ldhS5Ms_Sf7yK8VPQQ"

ACTIVE_DEALS = {}

CURRENCY, AMOUNT, DESCRIPTION, PARTNER = range(4)

STATUS_NAMES = {
    "created": "🟡 Ожидает подключения покупателя",
    "accepted": "🔵 Ожидает оплаты покупателем",
    "paid": "🟣 Оплачена (ожидает товар)",
    "item_transferred": "🟠 Товар передан (на проверке)",
    "completed": "🟢 Завершена",
    "rejected": "🔴 Отклонена",
}

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤝 Создать сделку", callback_data="create_deal")],
        [InlineKeyboardButton("📜 Мои сделки", callback_data="my_deals"), InlineKeyboardButton("💳 Баланс", callback_data="balance")],
        [InlineKeyboardButton("📖 Принцип работы", callback_data="how_it_works"), InlineKeyboardButton("💬 Поддержка", callback_data="support")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0].startswith("deal_"):
        deal_id = context.args[0].replace("deal_", "")
        deal = ACTIVE_DEALS.get(deal_id)
        if not deal:
            msg = "❌ <b>Сделка не найдена или уже завершена.</b>"
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(msg, parse_mode="HTML")
            else:
                await update.message.reply_text(msg, parse_mode="HTML")
            return ConversationHandler.END

        text = (
            f"📩 <b>Вам поступило предложение о сделке!</b>\n\n"
            f"👤 <b>Продавец:</b> {deal['creator']}\n"
            f"💰 <b>Сумма:</b> {deal['amount']} {deal['currency']}\n"
            f"📝 <b>Описание:</b> {deal['description']}\n"
            f"📌 <b>Статус:</b> Ожидает подтверждения\n\n"
            "Вы подтверждаете участие в сделке?"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Принять сделку", callback_data=f"accept_deal_{deal_id}")],
            [InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_deal_{deal_id}")]
        ])
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await update.message.reply_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        return ConversationHandler.END

    caption_text = (
        "💎 <b>Добро пожаловать на FunPay</b>\n\n"
        "Ваш надёжный P2P-гарант:\n"
        "▫️ <b>Автоматические сделки</b> с NFT и подарками\n"
        "▫️ <b>Полная защита</b> обеих сторон\n"
        "▫️ <b>Передача товаров</b> через менеджера: @FunPayBankRobot\n\n"
        "👇 <i>Выберите действие ниже:</i>"
    )

    chat_id = update.callback_query.message.chat_id if update.callback_query else update.message.chat_id

    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.message.delete()
        except Exception:
            pass

    try:
        await context.bot.send_animation(
            chat_id=chat_id,
            animation=WELCOME_GIF_ID,
            caption=caption_text,
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.warning(f"Ошибка отправки анимации: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=caption_text,
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    return ConversationHandler.END

async def start_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 TON", callback_data="curr_TON"), InlineKeyboardButton("🇷🇺 RUB", callback_data="curr_RUB"), InlineKeyboardButton("⭐ Stars", callback_data="curr_Stars")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_deal")]
    ])
    try:
        await query.message.delete()
    except Exception:
        pass
    await context.bot.send_message(chat_id=query.message.chat_id, text="🤝 <b>Создание сделки [1/4]</b>\n\nВыберите валюту проведения сделки:", reply_markup=keyboard, parse_mode="HTML")
    return CURRENCY

async def select_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    currency = query.data.split("_")[1]
    context.user_data["deal_currency"] = currency
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="cancel_deal")]])
    await query.edit_message_text(text=f"🤝 <b>Создание сделки [2/4]</b>\n\nВыбрана валюта: <b>{currency}</b>\n\nВведите сумму сделки в <b>{currency}</b>:", reply_markup=keyboard, parse_mode="HTML")
    return AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["deal_amount"] = update.message.text
    currency = context.user_data.get("deal_currency", "")
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="cancel_deal")]])
    await update.message.reply_text(text=f"📝 <b>Создание сделки [3/4]</b>\n\nСумма: <b>{update.message.text} {currency}</b>\n\nВведите подробное <b>описание товара</b> или условий сделки:", reply_markup=keyboard, parse_mode="HTML")
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["deal_description"] = update.message.text
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="cancel_deal")]])
    await update.message.reply_text(text="👤 <b>Создание сделки [4/4]</b>\n\nУкажите <b>@username</b> покупателя:", reply_markup=keyboard, parse_mode="HTML")
    return PARTNER

async def get_partner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    partner = update.message.text
    if not partner.startswith("@"):
        partner = f"@{partner}"
    currency = context.user_data.get("deal_currency")
    amount = context.user_data.get("deal_amount")
    description = context.user_data.get("deal_description")
    deal_id = str(uuid.uuid4())[:8]

    ACTIVE_DEALS[deal_id] = {
        "creator_id": update.message.from_user.id,
        "creator": f"@{update.message.from_user.username}" if update.message.from_user.username else update.message.from_user.first_name,
        "partner": partner,
        "buyer_id": None,
        "currency": currency,
        "amount": amount,
        "description": description,
        "status": "created",
    }
    bot_info = await context.bot.get_me()
    deal_link = f"https://t.me/{bot_info.username}?start=deal_{deal_id}"
    summary_text = (
        f"✅ <b>Сделка успешно сформирована!</b>\n\n"
        f"🆔 <b>ID сделки:</b> <code>{deal_id}</code>\n"
        f"💰 <b>Сумма:</b> {amount} {currency}\n"
        f"📝 <b>Описание:</b> {description}\n"
        f"👤 <b>Покупатель:</b> {partner}\n"
        f"📌 <b>Статус:</b> Ожидает подключения покупателя\n\n"
        f"🔗 <b>Ссылка для покупателя:</b>\n<code>{deal_link}</code>\n\n"
        "<i>Отправьте эту ссылку покупателю.</i>"
    )
    await update.message.reply_text(text=summary_text, reply_markup=get_main_keyboard(), parse_mode="HTML")
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Создание сделки отменено.")
    context.user_data.clear()
    await start(update, context)
    return ConversationHandler.END

async def deal_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("accept_deal_"):
        deal_id = data.replace("accept_deal_", "")
        deal = ACTIVE_DEALS.get(deal_id)
        if deal:
            deal["status"] = "accepted"
            deal["buyer_id"] = query.from_user.id
            buyer_name = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
            try:
                await context.bot.send_message(chat_id=deal["creator_id"], text=f"🎉 <b>Покупатель {buyer_name} принял сделку №<code>{deal_id}</code>!</b>\n\n💰 Сумма: {deal['amount']} {deal['currency']}\n📌 Статус: <i>Ожидается оплата покупателем</i>", parse_mode="HTML")
            except Exception:
                pass
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("💳 Заказ оплачен", callback_data=f"paid_{deal_id}")]])
            await query.edit_message_text(f"✅ <b>Вы приняли сделку №<code>{deal_id}</code>!</b>\n\n💰 <b>Сумма к оплате:</b> {deal['amount']} {deal['currency']}\n👨‍💻 <b>Гарант:</b> @FunPayBankRobot\n\nПроизведите оплату гаранту, после чего нажмите кнопку ниже:", reply_markup=keyboard, parse_mode="HTML")

    elif data.startswith("paid_"):
        deal_id = data.replace("paid_", "")
        deal = ACTIVE_DEALS.get(deal_id)
        if deal:
            deal["status"] = "paid"
            buyer_name = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
            seller_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📦 Товар передан гаранту", callback_data=f"item_sent_{deal_id}")]])
            seller_text = (
                f"💸 <b>Заказ №<code>{deal_id}</code> оплачен со стороны покупателя!</b>\n\n"
                f"👤 <b>Покупатель:</b> {buyer_name}\n"
                f"💰 <b>Сумма:</b> {deal['amount']} {deal['currency']}\n"
                f"📌 <b>Статус:</b> Ожидает передачи товара продавцом\n\n"
                "⚠️ <b>Теперь ваша очередь!</b> Передайте товар/NFT гаранту @FunPayBankRobot, после чего нажмите кнопку ниже:"
            )
            try:
                await context.bot.send_message(chat_id=deal["creator_id"], text=seller_text, reply_markup=seller_keyboard, parse_mode="HTML")
            except Exception as e:
                logging.error(f"Ошибка отправки: {e}")
            await query.edit_message_text("⌛ <b>Заказ переведён в статус «Оплачен»!</b>\n\nПродавец получил уведомление о необходимости передать товар гаранту @FunPayBankRobot.\nОжидайте передачи товара.", parse_mode="HTML")

    elif data.startswith("item_sent_"):
        deal_id = data.replace("item_sent_", "")
        deal = ACTIVE_DEALS.get(deal_id)
        if deal:
            deal["status"] = "item_transferred"
            if deal.get("buyer_id"):
                try:
                    await context.bot.send_message(chat_id=deal["buyer_id"], text=f"📦 <b>Продавец передал товар гаранту по сделке №<code>{deal_id}</code>!</b>\n\n📌 <b>Статус:</b> Идет проверка гарантом @FunPayBankRobot.\nОжидайте получения товара и завершения сделки.", parse_mode="HTML")
                except Exception:
                    pass
            await query.edit_message_text(f"✅ <b>Информация принята!</b>\n\nСделка №<code>{deal_id}</code> переведена в статус проверки.\nГарант @FunPayBankRobot проверит товар и завершит сделку.", parse_mode="HTML")

    elif data.startswith("reject_deal_"):
        deal_id = data.replace("reject_deal_", "")
        deal = ACTIVE_DEALS.get(deal_id)
        if deal:
            deal["status"] = "rejected"
            try:
                await context.bot.send_message(chat_id=deal["creator_id"], text=f"❌ <b>Покупатель отклонил сделку №<code>{deal_id}</code>.</b>", parse_mode="HTML")
            except Exception:
                pass
            await query.edit_message_text(f"❌ Вы отклонили сделку №<code>{deal_id}</code>.", parse_mode="HTML")

async def my_deals_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_handle = f"@{query.from_user.username}" if query.from_user.username else None

    user_deals = []
    for d_id, deal in ACTIVE_DEALS.items():
        if deal.get("creator_id") == user_id or deal.get("buyer_id") == user_id:
            user_deals.append((d_id, deal))
        elif user_handle and deal.get("partner") == user_handle:
            user_deals.append((d_id, deal))

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]])
    try:
        await query.message.delete()
    except Exception:
        pass

    if not user_deals:
        await context.bot.send_message(chat_id=query.message.chat_id, text="📜 <b>У вас пока нет активных сделок.</b>\n\nСоздайте новую сделку или перейдите по ссылке от продавца.", reply_markup=keyboard, parse_mode="HTML")
        return

    text_lines = ["📜 <b>Ваши текущие сделки:</b>\n"]
    for d_id, deal in user_deals:
        role = "Продавец" if deal.get("creator_id") == user_id else "Покупатель"
        status_str = STATUS_NAMES.get(deal.get("status"), deal.get("status"))
        text_lines.append(f"🔹 <b>Сделка №<code>{d_id}</code></b> ({role})\n💰 Сумма: <b>{deal['amount']} {deal['currency']}</b>\n📌 Статус: {status_str}\n")

    await context.bot.send_message(chat_id=query.message.chat_id, text="\n".join(text_lines), reply_markup=keyboard, parse_mode="HTML")

async def navigation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "main_menu":
        await start(update, context)

    elif query.data == "my_deals":
        await my_deals_handler(update, context)

    elif query.data in ["balance", "how_it_works", "support"]:
        try:
            await query.message.delete()
        except Exception:
            pass
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]])

        if query.data == "balance":
            user = query.from_user
            text = f"💳 <b>Ваш баланс</b>\n\n👤 Пользователь: <b>{user.first_name}</b> (<code>{user.id}</code>)\n💎 TON: <b>0.00</b>\n🇷🇺 RUB: <b>0.00</b>\n⭐ Stars: <b>0</b>"
        elif query.data == "how_it_works":
            text = (
                "📖 <b>Подробный принцип работы P2P-гаранта FunPay</b>\n\n"
                "Наша система создана для безопасного проведения сделок с цифровыми товарами, "
                "NFT и подарками без риска быть обманутым.\n\n"
                "<b>📌 Пошаговый алгоритм сделки:</b>\n"
                "1️⃣ <b>Создание:</b> Продавец нажимает «Создать сделку», указывает валюту, сумму, "
                "описание товара и отправляет сгенерированную ссылку покупателю.\n"
                "2️⃣ <b>Подключение:</b> Покупатель переходит по ссылке, проверяет условия и подтверждает участие.\n"
                "3️⃣ <b>Оплата:</b> Покупатель переводит средства на баланс гаранта (@FunPayBankRobot) "
                "и нажимает кнопку подтверждения оплаты.\n"
                "4️⃣ <b>Передача товара:</b> После поступления средств продавец передает товар (NFT/подарок) "
                "нашему официальному гаранту и подтверждает отправку.\n"
                "5️⃣ <b>Завершение:</b> Гарант проверяет корректность переданного актива и моментально "
                "переводит криптовалюту/средства продавцу.\n\n"
                "🛡 <i>Все споры и спорные ситуации оперативно решаются через нашу службу поддержки 24/7.</i>"
            )
        elif query.data == "support":
            text = "💬 <b>Служба поддержки:</b> @FunPayBankRobot\nВремя работы: 24/7"

        await context.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=keyboard, parse_mode="HTML")

def main():
    print("Запуск бота...")
    app = Application.builder().token(TOKEN).build()

    deal_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_deal, pattern="^create_deal$")],
        states={
            CURRENCY: [CallbackQueryHandler(select_currency, pattern="^curr_")],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
            PARTNER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_partner)],
        },
        fallbacks=[CallbackQueryHandler(cancel_deal, pattern="^cancel_deal$"), CommandHandler("start", start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(deal_conv_handler)
    app.add_handler(CallbackQueryHandler(deal_action_handler, pattern="^(accept_deal_|reject_deal_|paid_|item_sent_)"))
    app.add_handler(CallbackQueryHandler(navigation_handler, pattern="^(main_menu|my_deals|balance|how_it_works|support)$"))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
      
