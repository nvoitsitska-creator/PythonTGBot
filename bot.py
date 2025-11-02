import re
from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder,CallbackQueryHandler,ContextTypes,CommandHandler,MessageHandler,filters
import logging
from gpt import ChatGPTService
from util import (load_message,load_prompt,send_text,send_image,show_main_menu,
                  default_callback_handler,send_text_buttons)
from credentials import ChatGPT_TOKEN,BOT_TOKEN
import os
import asyncio


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
        "quiz": "Візьми участь у квізі",
        "translate": "Перекладу текст"
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
        "star_shevchenko": "Тарас Шевченко 📖",
        "star_monro": "Мерлін Монро 👩",
        "star_enshtein": "Альберт Енштейн  🧐",
        "star_opra": "Опра Вімфрі 💃",
        "star_vinchi": "Леонардо ДаВінчі 🧑‍🎨",
        "start": "⬅️ Повернутися у Головне меню"
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
        await send_text(update,context,"На жаль, виникла помилка при завантаженні відповіді.")
        return

    context.user_data['current_star'] = data
    context.user_data['mode'] = 'star'

    star_title = {
        "star_shevchenko": "Тарас Шевченко 📖",
        "star_monro": "Мерлін Монро 👩",
        "star_enshtein": "Альберт Енштейн  🧐",
        "star_opra": "Опра Вімфрі 💃",
        "star_vinchi": "Леонардо ДаВінчі 🧑‍🎨",
        "start": "⬅️ Повернутися у Головне меню"
    }
    ukr_star_title = star_title.get(data, data)
    await send_text_buttons(
        update,
        context,
        f"👤 Ви почали розмову з {ukr_star_title}.\nНадішліть повідомлення, щоб отримати відповідь.",
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
        button = {
            'start': 'Завершити'}
        answer = await chat_gpt.send_question(prompt, text)
        await send_text_buttons(update, context, f"Відповідь зірки:\n{answer}", button)
    except Exception as e:
        logger.error(f'Помилка під час діалогу із зіркою: {e}')
        await send_text(update,context,'Виникла помилка під час спілкування. Спробуйте ще раз.')

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['mode'] = 'quiz'
    msg = load_message('quiz')
    await send_image(update, context, 'quiz')
    await send_text_buttons(update, context, msg, {
        "quiz_general":"Загальні знання",
        "quiz_history":"Історичні факти та дати",
        "quiz_science":"Наукові відкриття",
        "quiz_art":"Культура і мистецтво",
        "start":"⬅️ Повернутись у головне меню"
    })

async def quiz_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    await send_image(update, context, data)
    await send_text(update, context,"Гарний вибір!")

    prompt = load_prompt(data)
    if not prompt:
        await send_text(update,context,"⚠️ Не вдалося завантажити тему квізу.")
        return

    chat_gpt.set_prompt(prompt)
    context.user_data['current_quiz'] = data
    context.user_data['mode'] = 'quiz'
    context.user_data['score']=0
    context.user_data['question_number']=1

    quiz_titles = {
        "quiz_general": "Загальні знання",
        "quiz_history": "Історичні факти та дати",
        "quiz_science": "Наукові відкриття",
        "quiz_art": "Культура і мистецтво"
    }
    ukr_title = quiz_titles.get(data, data)
    await send_text(update,context,f"👤 Ви почали квіз на тему {ukr_title}.\nПерше питання вже готується.")
    await ask_quiz_question(update,context)

async def ask_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_quiz = context.user_data.get("current_quiz")
    prompt = load_prompt(current_quiz)
    question_text = await chat_gpt.send_question(
        prompt,
        "Згенеруй одне коротке питання для квізу з 4 варіантами відповідей (A–D) "
        "і вкажи правильну відповідь у кінці."
    )
    parts = question_text.split("Правильна відповідь:")
    only_question = parts[0].strip()
    await send_text(update, context, only_question)

    match = re.search(r"Правильна відповідь:\s*([A-D])", question_text)
    if match:
        context.user_data["correct_answer"] = match.group(1).upper()
    else:
        context.user_data["correct_answer"] = None

async def quiz_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.effective_message
    user_answer = (message.text or "").strip().upper()
    if not user_answer or user_answer[0] not in "ABCD":
        await send_text(update,context,"❌ Будь ласка, введіть одну літеру від A до D.")
        return
    user_answer = user_answer[0]
    correct = context.user_data.get("correct_answer")
    if not correct:
        await send_text(update,context,"⚠️ Спочатку дочекайтесь питання.")
        return
    correct_letter = correct.strip().upper()[0]

    if user_answer == correct_letter:
        context.user_data["score"] += 1
        await send_image(update,context,"correct_answer")
        result_text = f"✅ Правильно! Поточний рахунок: {context.user_data['score']}"
    else:
        await send_image(update, context, "wrong_answer")
        result_text = f"❌ Неправильно. Правильна відповідь: {correct}.Поточний рахунок: {context.user_data['score']}"

    await send_text_buttons(update,context,result_text,{
        "quiz_dialog": "Продовжити",
        "quiz_button": "Змінити тему",
        "start": "Повернутися у головне меню"
    })

    context.user_data["question_number"]= context.user_data.get("question_number",0) + 1

async def quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "quiz_dialog":
        await send_text(update, context, "🔄 Готую наступне питання...")
        await ask_quiz_question(update, context)
    elif data == "quiz_button":
        await quiz(update,context)
    elif data == "start":
        await show_main_menu(update, context)
    else:
        await send_text(update, context, "Натисніть необхідні кнопку")


async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['mode'] = 'translate'
    msg = load_message('translate')
    await send_image(update, context, 'translate')
    await send_text_buttons(update, context, msg, {
        "translate_english": "Англійську 🇬🇧",
        "translate_spanish": "Іспанську 🇪🇦",
        "translate_polish": "Польську 🇵🇱",
        "translate_arabic": "Арабську 🇦🇪",
        "start": "⬅️ Повернутись у головне меню"
    })

async def languages_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()
    try:
        await send_image(update, context, data)
    except FileNotFoundError:
        await send_text(update,context, "Зображення не знайдено, але я все одно можу перекласти твій текст 🙂")

    try:
        prompt = load_prompt(data)
        chat_gpt.set_prompt(prompt)
    except Exception as e:
        logger.error(f'Не вдалося завантажити промпт для {data}: {e}')
        await send_text(update,context,"На жаль, виникла помилка при завантаженні відповіді.")
        return

    context.user_data['current_language'] = data
    context.user_data['mode'] = 'translate'

    language_titles = {
        "translate_english": "Англійську",
        "translate_spanish": "Іспанську",
        "translate_polish": "Польську",
        "translate_arabic": "Арабську",
    }
    chose_language = language_titles.get(data, data)
    await send_text_buttons(
        update,
        context,
        f"👤 Ви обрати {chose_language} мову.\nНадішліть текст, щоб отримати переклад.",
        {"start": "⬅️ Повернутись у головне меню"}
    )

async def translate_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        choose_language = context.user_data.get('current_language')
        if not choose_language:
            await send_text(update, context, "Будь ласка, спершу оберіть мову.")
            return

        prompt = load_prompt(choose_language)

        answer = await chat_gpt.send_question(prompt, text)
        buttons = {
            'languages_button': 'Хочу обрати іншу мову',
            'start': 'Завершити'}

        await send_text_buttons(update, context,answer,buttons)
        # await send_text(update, context, answer)

    except Exception as e:
        logger.error(f'Помилка під час перекладу: {e}')
        await send_text(update,context,'Виникла помилка під час перекладу. Спробуйте ще раз.')

async def translate_buttons(update:Update,context:ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "languages_button":
        await translate(update,context)
    elif data == "start":
        await start(update,context)

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get('mode')
    if mode == 'gpt':
        await gpt_dialog(update,context)
    elif mode == 'star':
        await star_dialog(update,context)
    elif mode == 'quiz':
        await quiz_dialog(update,context)
    elif mode == "translate":
        await translate_answer(update,context)
    else:
        await send_text(update,context, "Будь ласка, оберіть команду з меню.")

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("random", random_fact))
app.add_handler(CallbackQueryHandler  (random_buttons, pattern="^(random|start)$"))
app.add_handler(CallbackQueryHandler  (quiz_callback, pattern="^(quiz_dialog|quiz_button|start)$"))
app.add_handler(CallbackQueryHandler  (translate_buttons, pattern="^(languages_button|start)$"))
app.add_handler(CommandHandler("gpt", gpt))
app.add_handler(CommandHandler("talk", dialog_with_star))
app.add_handler(CommandHandler("quiz", quiz))
app.add_handler(CommandHandler("translate", translate))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, hello))
app.add_handler(CallbackQueryHandler(star_button, pattern= "^star_"))
app.add_handler(CallbackQueryHandler(quiz_button, pattern= "^quiz_"))
app.add_handler(CallbackQueryHandler(languages_button, pattern= "^translate_"))



app.run_polling()