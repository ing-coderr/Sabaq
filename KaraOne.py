from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, PreCheckoutQueryHandler, CallbackQueryHandler
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# States for the conversation
SELECT_MENU, GET_PHONE, GET_PEOPLE_COUNT, GET_CURRENT_LOCATION, CANCEL_ORDER = range(5)
order_counter = 0

# Channels for messages
CHANNEL_INTER_REGIONAL = '@hello_world_0004'
CHANNEL_INTRA_REGIONAL = '@hello_world_003'

orders = {}

def create_inline_keyboard(buttons):
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=data) for text, data in row] for row in buttons])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"Assalawma Aleykum, {user_name}! Qayerge bariwdi qaleysiz?",
        reply_markup=ReplyKeyboardMarkup(
            [['Rayonga', 'Rayon ishinde'], ['Biykarlaw']],
            one_time_keyboard=False, resize_keyboard=True
        )
    )
    return SELECT_MENU

async def select_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    selected_menu = update.message.text
    if selected_menu == 'Biykarlaw':
        return await cancel(update, context)

    context.user_data['selected_menu'] = selected_menu
    await update.message.reply_text(
        "Iltimas telefon nom kirgizin:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton('Telefon nom jiberiw', request_contact=True)], ['Biykarlaw']],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return GET_PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == 'Biykarlaw':
        return await cancel(update, context)

    user_phone = update.message.contact.phone_number
    context.user_data['phone'] = user_phone

    await update.message.reply_text(
        "Menudan neshe adam ekeninizdi tanlan:",
        reply_markup=ReplyKeyboardMarkup(
            [['1', '2', '3', '4', '5'], ['Biykarlaw']],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return GET_PEOPLE_COUNT

async def get_people_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == 'Biykarlaw':
        return await cancel(update, context)

    people_count = update.message.text
    context.user_data['people_count'] = people_count
    await update.message.reply_text(
        "Hazirgi jaylasqan jerinisti jiberin:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton('Jaylasiwdi jiberiw', request_location=True)], ['Biykarlaw']],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return GET_CURRENT_LOCATION

async def get_current_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == 'Biykarlaw':
        return await cancel(update, context)

    global order_counter
    user_location = update.message.location
    current_location = (user_location.latitude, user_location.longitude)
    context.user_data['current_location'] = current_location

    order_counter += 1
    order_id = order_counter
    context.user_data['order_id'] = order_id

    user_name = update.message.from_user.first_name
    user_phone = context.user_data['phone']
    people_count = context.user_data['people_count']

    message = (
        f"Buyurtpa nom: {order_id}\n"
        f"Paydalanuwshi: {user_name}\n"
        f"Telefon: {user_phone}\n"
        f"Adamlar sani: {people_count}\n"
        f"Hazirgi jaylasuwi: https://maps.google.com/?q={current_location[0]},{current_location[1]}\n"
        f"Arzani qabillaw ushun iltimas tolemdi amelge asirin\n"
    )

    if context.user_data['selected_menu'] == 'Rayonga':
        CHANNEL_ID = CHANNEL_INTER_REGIONAL
    else:
        CHANNEL_ID = CHANNEL_INTRA_REGIONAL

    reply_markup = create_inline_keyboard([
        [("Tolew", f"pay_{order_id}")]
    ])

    sent_message = await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=message,
        reply_markup=reply_markup
    )

    orders[order_id] = {
        'channel_id': CHANNEL_ID,
        'message_id': sent_message.message_id,
        'user_id': update.message.chat_id
    }

    await update.message.reply_text("Sizdin arzaniz qabillandi tez arada siz benen baylanisamiz")
    return CANCEL_ORDER

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    order_id = int(query.data.split('_')[1])

    if order_id in orders:
        channel_id = orders[order_id]['channel_id']
        message_id = orders[order_id]['message_id']

        reply_markup = create_inline_keyboard([
            [("Tolemdi amelge asiriw", f"pay_invoice_{order_id}")]
        ])

        await context.bot.edit_message_text(
            chat_id=channel_id,
            message_id=message_id,
            text=(
                f"Buyirtpa nom: {order_id}\n"
                f"\n"
                f"Xizmet haqqi: 1000 som"
            ),
            reply_markup=reply_markup
        )

async def send_payment_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    order_id = int(query.data.split('_')[2])

    if order_id in orders:
        channel_id = orders[order_id]['channel_id']

        title = "Xizmet haqqi"
        description = "Buyirtpani qabillaw ushun tolemdi amelge asirin:"
        payload = f"order_{order_id}"
        currency = "UZS"
        prices = [LabeledPrice("Xizmet haqqi", 1000 * 100)]

        await context.bot.send_invoice(
            chat_id=channel_id,
            title=title,
            description=description,
            payload=payload,
            provider_token="398062629:TEST:999999999_F91D8F69C042267444B74CC0B3C747757EB0E065",
            currency=currency,
            prices=prices,
            start_parameter=f"order-{order_id}"
        )

async def pre_checkout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payment_info = update.message.successful_payment
    payload = payment_info.invoice_payload
    order_id = int(payload.split('_')[1])

    if order_id in orders:
        channel_id = orders[order_id]['channel_id']
        message_id = orders[order_id]['message_id']
        user_id = orders[order_id]['user_id']

        await context.bot.edit_message_text(
            chat_id=channel_id,
            message_id=message_id,
            text="Tolem amelge asirildi.Arza qabillandi"
        )

        await context.bot.send_message(
            chat_id=user_id,
            text="Arzaniz qabillandi biz joldamiz"
        )

        del orders[order_id]

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Chat toqtatildi /start")
    return ConversationHandler.END

def main():
    TOKEN = 'Bul_Token_Ushin_Orin'
    application = Application.builder().token(TOKEN).build()

    application.add_handler(PreCheckoutQueryHandler(pre_checkout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    application.add_handler(CallbackQueryHandler(handle_payment, pattern=r"^pay_\d+"))
    application.add_handler(CallbackQueryHandler(send_payment_invoice, pattern=r"^pay_invoice_\d+"))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_menu)],
            GET_PHONE: [MessageHandler(filters.CONTACT, get_phone)],
            GET_PEOPLE_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_people_count)],
            GET_CURRENT_LOCATION: [MessageHandler(filters.LOCATION, get_current_location)],
            CANCEL_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, cancel)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()
