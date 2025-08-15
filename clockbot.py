from aiogram.filters import Command
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime, timedelta
import asyncio
import requests
import logging
import random
import string

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

API_TOKEN = '8130975273:AAE6GDAcZsmUCTQOJ3kfim0680SPYtAnmVQ'  # Твой токен
ADMIN_ID = 50371663  # Твой Telegram ID
DATA_FILE = 'clients.txt'
USERS_FILE = "users.txt"
USED_TOKENS_FILE = 'used_tokens.txt'
PROMO_URL = ''  # Укажи ссылку на акции или оставь пустым
last_promo_text = ""

facts_for_clock = [
    'Первые часы: Самые ранние механические часы появились в Европе в XIII веке. Они были большими башенными часами, установленными в церквях и монастырях.',
    'Карманные часы: В XVI веке немецкий часовщик Питер Хенляйн создал первые портативные часы, которые стали предшественниками современных наручных часов.',
    'Наручные часы: Наручные часы стали популярны только в начале XX века, особенно после Первой мировой войны, когда солдаты оценили их удобство.',
    'Кварцевый прорыв: В 1969 году компания Seiko представила первые кварцевые часы, которые обеспечили небывалую точность хода.',
    'Самые дорогие часы: Часы Graff Diamonds Hallucination стоят 55 миллионов долларов и украшены 110 каратами редких бриллиантов.',
    'Часы в космосе: Omega Speedmaster Professional стали первыми часами, побывавшими на Луне во время миссии Apollo 11 в 1969 году.',
    'Антикварная ценность: Часы Patek Philippe Henry Graves Supercomplication, созданные в 1933 году, были проданы на аукционе за 24 миллиона долларов в 2014 году.',
    'Водонепроницаемость: Первые водонепроницаемые часы, Rolex Oyster, были представлены в 1926 году. Их испытала пловчиха Мерседес Гляйтце, переплыв Ла-Манш.',
    'Автоматический механизм: Первые автоматические часы с автоподзаводом были изобретены в 1770 году, но массовое производство началось только в XX веке.',
    'Часы без стрелок: Современные бренды, такие как Ressence, создают часы без традиционных стрелок, используя вращающиеся диски для отображения времени.',
    'Швейцарское мастерство: Швейцария производит около 30 миллионов часов в год, что составляет лишь 2% от мирового производства, но доминирует в сегменте люксовых часов.',
    'Часы с турбийоном: Турбийон, изобретенный в 1795 году Абрахамом-Луи Брегетом, компенсирует влияние гравитации, повышая точность механических часов.',
    'Солнечные часы: Самые древние часы — солнечные — использовались еще в Древнем Египте около 1500 года до н.э.',
    'Атомные часы: Самые точные часы в мире, атомные, ошибаются на 1 секунду за 100 миллионов лет. Они используются для синхронизации GPS и интернета.',
    'Умные часы: Первые смарт-часы, IBM WatchPad, появились в 2001 году, но настоящую популярность этот сегмент обрел с выходом Apple Watch в 2015 году.'
]

user_context = {}
pending_requests = {}
pending_spend_requests = {}

dp = Dispatcher()
bot = Bot(token=API_TOKEN)

def add_user_id(user_id):
    user_id = str(user_id)
    try:
        with open(USERS_FILE, "r+", encoding="utf-8") as f:
            ids = f.read().splitlines()
            if user_id not in ids:
                f.write(user_id + "\n")
                logging.info(f"Добавлен user_id: {user_id}")
    except FileNotFoundError:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            f.write(user_id + "\n")
            logging.info(f"Создан {USERS_FILE}, добавлен user_id: {user_id}")

def get_all_user_ids():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logging.warning(f"{USERS_FILE} не найден, возвращён пустой список")
        return []

def today_str():
    return datetime.now().strftime("%Y-%m-%d")

def is_expired(date_str):
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        return (datetime.now() - date) > timedelta(days=180)
    except ValueError:
        logging.error(f"Неверный формат даты: {date_str}")
        return True

def get_promo_text():
    if not PROMO_URL:
        return "Акции не настроены."
    try:
        response = requests.get(PROMO_URL, timeout=10)
        response.encoding = 'utf-8'
        return response.text.strip()
    except Exception as e:
        logging.error(f"Ошибка загрузки акции: {e}")
        return "Не удалось загрузить акцию. Попробуйте позже."

def load_clients():
    clients = {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            if not line.startswith("bonus:"):
                parts = line.split(",")
                if len(parts) >= 2:
                    token = parts[0]
                    clients[token] = {
                        "token": token,
                        "telegram_id": parts[1],
                        "bonuses": []
                    }
            else:
                bonus_parts = line.split(":")
                if len(bonus_parts) == 3 and 'token' in locals():
                    if not is_expired(bonus_parts[2]):
                        clients[token]["bonuses"].append({
                            "amount": int(bonus_parts[1]),
                            "date": bonus_parts[2]
                        })
            i += 1
    except FileNotFoundError:
        logging.info(f"{DATA_FILE} не найден, создан пустой")
        open(DATA_FILE, "w", encoding="utf-8").close()
    except Exception as e:
        logging.error(f"Ошибка загрузки clients.txt: {e}")
    return clients

def save_clients(clients):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            for client in clients.values():
                valid_bonuses = [b for b in client["bonuses"] if not is_expired(b["date"])]
                client["bonuses"] = valid_bonuses
                f.write(f"{client['token']},{client['telegram_id']}\n")
                for b in valid_bonuses:
                    f.write(f"bonus:{b['amount']}:{b['date']}\n")
        logging.info("clients.txt успешно сохранён")
    except Exception as e:
        logging.error(f"Ошибка сохранения clients.txt: {e}")

def generate_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

def get_total_bonus(client):
    return sum(b["amount"] for b in client["bonuses"] if not is_expired(b["date"]))

def is_token_used(token):
    try:
        with open(USED_TOKENS_FILE, "r", encoding="utf-8") as f:
            used = f.read().splitlines()
            return token in used
    except FileNotFoundError:
        logging.info(f"{USED_TOKENS_FILE} не найден, создан пустой")
        open(USED_TOKENS_FILE, "w", encoding="utf-8").close()
    return False

def mark_token_used(token):
    try:
        with open(USED_TOKENS_FILE, "a", encoding="utf-8") as f:
            f.write(token + "\n")
        logging.info(f"Token {token} помечен как использованный")
    except Exception as e:
        logging.error(f"Ошибка записи в used_tokens.txt: {e}")

# Клавиатуры
keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='📍 Как нас найти', callback_data='geo')],
    [InlineKeyboardButton(text='🎁 Бонусы', callback_data='bonus')],
    [InlineKeyboardButton(text='🔥 Текущие акции', callback_data='action')],
    [InlineKeyboardButton(text='❓ Частые вопросы (FAQ)', callback_data='faq')]
])

faq_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🕰️ Интересные факты', callback_data='clock')],
    [InlineKeyboardButton(text='🚚 Есть ли доставка?', callback_data='delivery')],
    [InlineKeyboardButton(text='🕒 График работы', callback_data='work')],
    [InlineKeyboardButton(text='🏬 Как найти магазин', callback_data='where')],
    [InlineKeyboardButton(text='📩 Задать свой вопрос', callback_data='question')],
    [InlineKeyboardButton(text='⬅️ Назад', callback_data='back')]
])

bonus_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🆕 Зарегистрироваться', callback_data='registration')],
    [InlineKeyboardButton(text='🛍 Сообщить о покупке', callback_data='shopping')],
    [InlineKeyboardButton(text='💰 Проверить бонусы', callback_data='check_bonus')],
    [InlineKeyboardButton(text='⬅️ Назад', callback_data='back')]
])

def get_confirm_keyboard(user_id, is_spend=False):
    prefix = "spend_" if is_spend else "confirm_"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"{prefix}{user_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")]
    ])

@dp.message(Command('start'))
async def welcome(message: Message):
    user_id = message.from_user.id
    add_user_id(user_id)
    token = message.text.split()[-1] if len(message.text.split()) > 1 else None

    if token:
        if is_token_used(token):
            await message.answer(
                "Эта реферальная ссылка уже использована. Напишите в магазин.",
                parse_mode="HTML"
            )
            logging.warning(f"Попытка повторного использования token: {token} пользователем {user_id}")
            return

        clients = load_clients()
        if token in clients:
            await message.answer(
                "Вы уже зарегистрированы по этой ссылке.",
                parse_mode="HTML"
            )
            return

        clients[token] = {
            'token': token,
            'telegram_id': str(user_id),
            'bonuses': [{'amount': 50, 'date': today_str()}]
        }
        save_clients(clients)
        mark_token_used(token)
        await message.answer(
            f"🎉 Вы зарегистрированы по реферальной ссылке!\n\n"
            f"Ваш token: {token}\n\n"
            f"Вам зачислено 50 бонусов за регистрацию! Используйте их на любой товар (до 50% стоимости).\n\n"
            f"Выберите, что вас интересует 👇",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        logging.info(f"Регистрация user_id {user_id} по token {token}, +50 бонусов")
    else:
        await message.answer(
            f"🎉 Добро пожаловать в 'Час Ы'! ⌚\n\n"
            f"У нас самые лучшие часы в городе! 💎\n\n"
            f"Чтобы участвовать в программе лояльности, используйте реферальную ссылку из магазина.\n\n"
            f"Выберите, что вас интересует 👇",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

@dp.callback_query(F.data == 'geo')
async def gps(callback: CallbackQuery):
    await callback.message.answer(
        f"Проспект Генерала Острякова, 60\n\n"
        f"Мы на Яндекс картах: <a href=\"https://yandex.ru/maps/-/CHdXEEmx\">открыть</a>",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == 'bonus')
async def bonus_program(callback: CallbackQuery):
    await callback.message.answer(
        f"Собирайте бонусы — 5% от каждой покупки часов. Тратьте на любой товар в магазине!",
        reply_markup=bonus_keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == 'registration')
async def registration_info(callback: CallbackQuery):
    await callback.message.answer(
        f"Чтобы зарегистрироваться, используйте реферальную ссылку из магазина.",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == 'shopping')
async def ask_amount(callback: CallbackQuery):
    if not ADMIN_ID:
        await callback.message.answer(
            f"Ошибка: админ не указан. Напишите в магазин.",
            parse_mode="HTML"
        )
        logging.error("ADMIN_ID не указан")
        return
    await callback.message.answer(
        f"Введите сумму покупки в рублях (например: 8500)",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(F.text.isdigit())
async def receive(message: Message):
    if not ADMIN_ID:
        await message.answer(
            f"Ошибка: админ не указан. Напишите в магазин.",
            parse_mode="HTML"
        )
        logging.error("ADMIN_ID не указан")
        return
    amount = int(message.text)
    if amount < 500:
        await message.answer(
            f"Сумма покупки слишком маленькая. Минимум - 500 руб.",
            parse_mode="HTML"
        )
        return

    bonus = int(amount * 0.05)
    user_id = message.from_user.id
    pending_requests[user_id] = {
        'amount': amount,
        'bonus': bonus,
        'telegram_id': str(user_id)
    }
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📢 Новая покупка!\n\n"
             f"Клиент: user_id {user_id}\n\n"
             f"Сумма: {amount} ₽\n\n"
             f"Бонусов: {bonus}",
        reply_markup=get_confirm_keyboard(user_id),
        parse_mode="HTML"
    )
    await message.answer(
        f"Заявка отправлена! Владелец подтвердит бонусы",
        parse_mode="HTML"
    )
    logging.info(f"Заявка на начисление: user_id {user_id}, сумма {amount}, бонусов {bonus}")

@dp.callback_query(F.data == "check_bonus")
async def check_bonus(callback: CallbackQuery):
    clients = load_clients()
    user_id = str(callback.from_user.id)
    for data in clients.values():
        if data["telegram_id"] == user_id:
            total = get_total_bonus(data)
            await callback.message.answer(
                f"У вас {total} бонусов.",
                parse_mode="HTML"
            )
            await callback.answer()
            return
    await callback.message.answer(
        f"Вы не зарегистрированы или данные не найдены.",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == 'use_bonus')
async def use_bonus(callback: CallbackQuery):
    if not ADMIN_ID:
        await callback.message.answer(
            f"Ошибка: админ не указан. Напишите в магазин.",
            parse_mode="HTML"
        )
        logging.error("ADMIN_ID не указан")
        return
    clients = load_clients()
    user_id = str(callback.from_user.id)
    for token, client in clients.items():
        if client["telegram_id"] == user_id:
            total = get_total_bonus(client)
            await callback.message.answer(
                f"У вас {total} бонусов. Введите сумму покупки (руб), чтобы использовать бонусы (до 50% стоимости):",
                parse_mode="HTML"
            )
            user_context['waiting_for_use_bonus'] = user_id
            await callback.answer()
            return
    await callback.message.answer(
        f"Вы не зарегистрированы. Сначала зарегистрируйтесь по реферальной ссылке!",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(F.text.isdigit(), lambda message: user_context.get('waiting_for_use_bonus') == str(message.from_user.id))
async def process_use_bonus(message: Message):
    user_id = str(message.from_user.id)
    amount = int(message.text)
    clients = load_clients()

    token = None
    for t, client in clients.items():
        if client["telegram_id"] == user_id:
            token = t
            break

    if token is None:
        await message.answer(
            f"Вы не зарегистрированы или данные не найдены.",
            parse_mode="HTML"
        )
        user_context.pop('waiting_for_use_bonus', None)
        return

    total_bonuses = get_total_bonus(clients[token])
    max_discount = amount // 2
    use_bonuses = min(total_bonuses, max_discount)

    if use_bonuses == 0:
        await message.answer(
            f"У вас недостаточно бонусов для45 использования.",
            parse_mode="HTML"
        )
        user_context.pop('waiting_for_use_bonus', None)
        return

    pending_spend_requests[user_id] = {
        'amount': amount,
        'use_bonuses': use_bonuses,
        'token': token
    }
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📢 Заявка на использование бонусов!\n\n"
                 f"От token {token}\n\n"
                 f"Сумма покупки: {amount} ₽\n\n"
                 f"Хочет использовать: {use_bonuses} бонусов",
            reply_markup=get_confirm_keyboard(user_id, is_spend=True),
            parse_mode="HTML"
        )
        await message.answer(
            f"Заявка на использование бонусов отправлена! Владелец подтвердит.",
            parse_mode="HTML"
        )
        logging.info(f"Заявка на списание: token {token}, {use_bonuses} бонусов, сумма {amount}")
    except Exception as e:
        await message.answer(
            f"Ошибка отправки заявки. Попробуйте позже.",
            parse_mode="HTML"
        )
        logging.error(f"Ошибка отправки заявки на списание: {e}")
    user_context.pop('waiting_for_use_bonus', None)

@dp.callback_query(F.data.startswith('confirm_'))
async def confirm_purchase(callback: CallbackQuery):
    clients = load_clients()
    user_id = int(callback.data.split('_')[1])
    if user_id not in pending_requests:
        await callback.message.edit_text(
            f"❌ Заявка не найдена",
            parse_mode="HTML"
        )
        logging.error(f"Заявка для user_id {user_id} не найдена")
        return

    client_found = None
    for code, client in clients.items():
        if client['telegram_id'] == str(user_id):
            client_found = client
            break

    if client_found:
        bonus = pending_requests[user_id]['bonus']
        client_found['bonuses'].append({
            'amount': bonus,
            'date': today_str()
        })
        save_clients(clients)
        await bot.send_message(
            user_id,
            f"🎉 Вам зачислено {bonus} бонусов!",
            parse_mode="HTML"
        )
        await callback.message.edit_text(
            f"✅ Покупка подтверждена. Бонусы зачислены! 🎊",
            parse_mode="HTML"
        )
        logging.info(f"Подтверждено начисление: user_id {user_id}, +{bonus} бонусов")
    else:
        await bot.send_message(
            user_id,
            f"Ошибка: клиент не найден",
            parse_mode="HTML"
        )
        await callback.message.edit_text(
            f"❌ Ошибка: клиент не найден",
            parse_mode="HTML"
        )
        logging.error(f"Клиент user_id {user_id} не найден")
    del pending_requests[user_id]

@dp.callback_query(F.data.startswith('spend_'))
async def confirm_spend(callback: CallbackQuery):
    clients = load_clients()
    user_id = int(callback.data.split('_')[1])
    if user_id not in pending_spend_requests:
        await callback.message.edit_text(
            f"❌ Заявка на списание не найдена",
            parse_mode="HTML"
        )
        logging.error(f"Заявка на списание для user_id {user_id} не найдена")
        return

    token = pending_spend_requests[user_id]['token']
    client_found = None
    for t, client in clients.items():
        if client['telegram_id'] == str(user_id):
            client_found = client
            break

    if client_found:
        use_bonuses = pending_spend_requests[user_id]['use_bonuses']
        total_bonuses = get_total_bonus(client_found)
        remaining_bonuses = total_bonuses - use_bonuses
        client_found['bonuses'] = []
        if remaining_bonuses > 0:
            client_found['bonuses'].append({
                'amount': remaining_bonuses,
                'date': today_str()
            })
        save_clients(clients)
        await bot.send_message(
            user_id,
            f"✅ Вы использовали {use_bonuses} бонусов! Остаток: {remaining_bonuses} бонусов.\n\n"
            f"Покажите token {token} в магазине для скидки.",
            parse_mode="HTML"
        )
        await callback.message.edit_text(
            f"✅ Использование бонусов подтверждено! 🎊",
            parse_mode="HTML"
        )
        logging.info(f"Подтверждено списание: token {token}, -{use_bonuses} бонусов, остаток {remaining_bonuses}")
    else:
        await bot.send_message(
            user_id,
            f"Ошибка: клиент не найден",
            parse_mode="HTML"
        )
        await callback.message.edit_text(
            f"❌ Ошибка: клиент не найден",
            parse_mode="HTML"
        )
        logging.error(f"Клиент user_id {user_id} не найден")
    del pending_spend_requests[user_id]

@dp.callback_query(F.data.startswith('reject_'))
async def reject_purchase(callback: CallbackQuery):
    user_id = int(callback.data.split('_')[1])
    if user_id in pending_requests:
        token = pending_requests[user_id].get('token', 'неизвестен')
        await bot.send_message(
            user_id,
            f"К сожалению, покупка не подтверждена. Обратитесь в магазин.",
            parse_mode="HTML"
        )
        await callback.message.edit_text(
            f"❌ Покупка отклонена.",
            parse_mode="HTML"
        )
        logging.info(f"Покупка для token {token} отклонена")
        del pending_requests[user_id]
    elif user_id in pending_spend_requests:
        token = pending_spend_requests[user_id]['token']
        await bot.send_message(
            user_id,
            f"К сожалению, использование бонусов не подтверждено. Обратитесь в магазин.",
            parse_mode="HTML"
        )
        await callback.message.edit_text(
            f"❌ Использование бонусов отклонено.",
            parse_mode="HTML"
        )
        logging.info(f"Списание бонусов для token {token} отклонено")
        del pending_spend_requests[user_id]
    else:
        await callback.message.edit_text(
            f"❌ Заявка не найдена",
            parse_mode="HTML"
        )
        logging.error(f"Заявка для user_id {user_id} не найдена")

@dp.callback_query(F.data == "action")
async def action(callback: CallbackQuery):
    global last_promo_text
    try:
        current_promo = get_promo_text()
        if last_promo_text == "":
            last_promo_text = current_promo
            await callback.message.answer(current_promo, parse_mode="HTML")
        elif current_promo != last_promo_text:
            for user_id in get_all_user_ids():
                try:
                    await bot.send_message(
                        user_id,
                        f"📢 У нас новая акция!\n\n"
                        f"🔥 Откройте «Текущие акции» → и получите скидку!",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logging.error(f"Не удалось отправить акцию user_id {user_id}: {e}")
            last_promo_text = current_promo
            await callback.message.answer(current_promo, parse_mode="HTML")
        else:
            await callback.message.answer(current_promo, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка обработки акции: {e}")
        await callback.message.answer(
            f"Сейчас нет активных акций.",
            parse_mode="HTML"
        )
    await callback.answer()

@dp.callback_query(F.data == 'faq')
async def faq_question(callback: CallbackQuery):
    await callback.message.answer(
        f"Задайте вопрос о нашем магазине или часах!",
        reply_markup=faq_keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == 'clock')
async def interesting_facts(callback: CallbackQuery):
    if not facts_for_clock:
        await callback.message.answer(
            f"Факты о часах временно недоступны.",
            parse_mode="HTML"
        )
        logging.error(f"Список facts_for_clock пуст")
        await callback.answer()
        return
    fact = random.choice(facts_for_clock)
    # Экранируем символы _, * для предотвращения ошибок парсинга
    fact = fact.replace('_', r'\_').replace('*', r'\*')
    await callback.message.answer(
        f"Интересный факт о часах:\n\n{fact}",
        parse_mode="HTML"
    )
    logging.info(f"Отправлен факт user_id {callback.from_user.id}: {fact}")
    await callback.answer()

@dp.callback_query(F.data == 'delivery')
async def faq_delivery(callback: CallbackQuery):
    await callback.message.answer(
        f"Магазин \"Час Ы\" не предоставляет услугу доставки",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == 'work')
async def faq_qwork(callback: CallbackQuery):
    await callback.message.answer(
        f"Мы работаем ежедневно с 10:00 до 18:30",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "where")
async def faq_where(callback: CallbackQuery):
    await callback.message.answer(
        f"Мы находимся в ТЦ \"Приветливый\" по адресу: проспект Генерала Острякова, 60.",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == 'question')
async def my_question(callback: CallbackQuery):
    if not ADMIN_ID:
        await callback.message.answer(
            f"Ошибка: админ не указан. Напишите в магазин.",
            parse_mode="HTML"
        )
        logging.error("ADMIN_ID не указан")
        return
    await callback.message.answer(
        f"📩 Вы можете задать любой вопрос.\n\n"
        f"Мы ответим в ближайшее время! ⏳",
        parse_mode="HTML"
    )
    user_context['waiting_for_question'] = callback.from_user.id
    await callback.answer()

@dp.message()
async def reply_to_user(message: Message):
    if user_context.get('waiting_for_question') == message.from_user.id:
        user_context.pop('waiting_for_question')
        try:
            fwd = await bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
            user_context[fwd.message_id] = message.from_user.id
            await message.answer(
                f"Ваш вопрос отправлен! Мы ответим в ближайшее время.",
                parse_mode="HTML"
            )
            logging.info(f"Вопрос от user_id {message.from_user.id} отправлен админу")
        except Exception as e:
            await message.answer(
                f"Не удалось отправить вопрос. Попробуйте позже.",
                parse_mode="HTML"
            )
            logging.error(f"Ошибка отправки вопроса от user_id {message.from_user.id}: {e}")
    elif message.from_user.id == ADMIN_ID and message.reply_to_message:
        user_id = user_context.get(message.reply_to_message.message_id)
        if user_id:
            try:
                await bot.copy_message(user_id, ADMIN_ID, message.message_id)
                await message.answer(
                    f"Ответ отправлен клиенту.",
                    parse_mode="HTML"
                )
                logging.info(f"Ответ отправлен user_id {user_id}")
            except Exception as e:
                await message.answer(
                    f"Не удалось отправить ответ.",
                    parse_mode="HTML"
                )
                logging.error(f"Ошибка отправки ответа user_id {user_id}: {e}")

@dp.callback_query(F.data == 'back')
async def background(callback: CallbackQuery):
    await callback.message.edit_text(
        f"Вы вернулись в главное меню. Выберите нужный раздел:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

async def main():
    logging.info("Бот 'Час Ы' запущен...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
