from tkinter.commondialog import Dialog

from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder,CallbackQueryHandler,ContextTypes,CommandHandler,MessageHandler,filters
import logging
from gpt import ChatGPTService
from util import (load_message,load_prompt,send_text,send_image,show_main_menu,
                  default_callback_handler,send_text_buttons)
from credentials import ChatGPT_TOKEN,BOT_TOKEN
from telegram.error import Conflict,NetworkError
from dotenv import load_dotenv
import os

logging.basicConfig(
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)

chat_gpt = ChatGPTService(token=ChatGPT_TOKEN)
app = ApplicationBuilder().token(BOT_TOKEN).build()

async def start(update:Update,context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} pressed /start")
    text = load_message('main')
    await send_image(update,context,'main')
    await send_text (update,context,text)
    await show_main_menu(update,context,{
        "start": "Головне меню",
        "random": "Дізнайся цікавий факт",
        "gpt": "Запитай у чату GPT",
        "talk": "Поговори з відомою особистістю",
        "quiz": "Візьми участь у квізі"
    })

async def random_fact(update:Update, context:ContextTypes.DEFAULT_TYPE):
    await send_image(update,context,'random')
    message = await send_text(update,context, "Зачекай. Я шукаю цікавий факт ...")

    try:
        prompt = load_prompt('random')
        fact = await chat_gpt.send_question(prompt, 'Напиши мені цікавий факт')
        buttons = {
            'random': 'Хочу ще один факт',
            'start': 'Завершити'}

        await context.bot.delete_message(chat_id = update.effective_chat.id,message_id=message.message_id)
        await send_text_buttons(update,context, f"Випадковий факт: \n\n{fact}", buttons)

    except Exception as e:
        logger.error(f"Помилка під час отримання цікавого факту: {e}")
        await send_text(update,context, "Нажаль виникла помилка. Спробуйте ще раз")
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id)


async def random_buttons(update:Update,context:ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "random":
        await random_fact(update,context)
    elif data == "start":
        await start(update,context)

async def gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['mode'] = 'gpt'
    prompt_text = load_prompt('gpt')
    chat_gpt.set_prompt(prompt_text)
    message = load_message('gpt')
    await send_image(update,context,'gpt')
    await send_text(update,context,message)

async def gpt_dialog(update,context):
    text = update.message.text
    prompt = load_prompt('gpt')
    answer = await chat_gpt.send_question(prompt,text)
    await send_text(update,context,answer)

async def dialog_with_star(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['mode'] = 'star'
    msg = load_message('star')
    await send_image(update,context,'star')
    await send_text_buttons(update,context, msg, {
        "star_shevchenko": "Тарас Шевченко",
        "star_monro": "Мерлін Монро",
        "star_opra": "Опра Вімфрі",
        "star_enshtein": "Альберт Енштейн",
        "star_vinchi": "Леонардо ДаВінчі",
    })

async def star_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()
    try:
        await send_image(update, context, data)
    except FileNotFoundError:
        await send_text(update,context, "Зображення не знайдено, але продовжимо розмову 🙂")

    await send_text(update, context,"Гарний вибір!")
    try:
        prompt = load_prompt(data)
        chat_gpt.set_prompt(prompt)
    except Exception as e:
        logger.error(f'Не вдалося завантажити промпт для {data}: {e}')
        await send_text(update,context,"На жаль, виникла помилка при завантаженні профілю особистості.")
        return

    context.user_data['current_star'] = data
    context.user_data['mode'] = 'star'

    personality_name = data.replace('star_', '').capitalize()
    await send_text_buttons(
        update,
        context,
        f"👤 Ви почали розмову з *{personality_name}*.\nНадішліть повідомлення, щоб отримати відповідь.",
        {"start": "⬅️ Повернутись у головне меню"}
    )

async def star_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        current_star = context.user_data.get('current_star')
        if not current_star:
            await send_text(update, context, "Будь ласка, спершу оберіть особистість.")
            return

        prompt = load_prompt(current_star)  # наприклад, star_vinchi.txt

        answer = await chat_gpt.send_question(prompt, text)
        await send_text(update, context, answer)
    except Exception as e:
        logger.error(f'Помилка під час діалогу із зіркою: {e}')
        await send_text(update,context,'Виникла помилка під час спілкування. Спробуйте ще раз.')

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get('mode')
    if mode == 'gpt':
        await gpt_dialog(update,context)
    elif mode == 'star':
        await star_dialog(update,context)


dialog = Dialog()
dialog.mode = None
dialog.list = []
dialog.user = {}
dialog.counter = 0

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("random", random_fact))
app.add_handler(CallbackQueryHandler  (random_buttons, pattern="^(random|start)$"))
app.add_handler(CommandHandler("gpt", gpt))
app.add_handler(CommandHandler("talk", dialog_with_star))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, hello))
app.add_handler(CallbackQueryHandler(star_button, pattern= "^star_"))



app.run_polling()