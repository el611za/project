import asyncio
import logging
from datetime import datetime, timedelta
import random
import string
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Логи в консоль
    ]
)

# Конфигурация
API_TOKEN = '8130975273:AAE6GDAcZsmUCTQOJ3kfim0680SPYtAnmVQ'  # Ваш Telegram токен
ADMIN_ID = 50371663  # Ваш Telegram ID
DATA_DIR = 'data'  # Папка для файлов
DATA_FILE = os.path.join(DATA_DIR, 'clients.txt')
USERS_FILE = os.path.join(DATA_DIR, 'users.txt')
USED_CODES_FILE = os.path.join(DATA_DIR, 'used_codes.txt')
PROMO_FILE = os.path.join(DATA_DIR, 'promotions.txt')

# Глобальные переменные
last_promo_text = "Акции пока не добавлены."
last_clients = {}
last_users = set()
last_used_codes = set()
user_context = {}
pending_requests = {}
pending_spend_requests = {}

# Факты о часах
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

dp = Dispatcher()
bot = Bot(token=API_TOKEN)

# Инициализация файлов
def init_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    for file in [DATA_FILE, USERS_FILE, USED_CODES_FILE, PROMO_FILE]:
        if not os.path.exists(file):
            with open(file, 'w', encoding='utf-8') as f:
                if file == PROMO_FILE:
                    f.write("Акции пока не добавлены.\n")
            logging.info(f"Создан файл: {file}")

# Работа с файлами
async def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logging.warning(f"Файл {file_path} не найден, создан пустой")
        with open(file_path, 'w', encoding='utf-8') as f:
            pass
        return ""
    except Exception as e:
        logging.error(f"Ошибка чтения {file_path}: {e}")
        return ""

async def write_file(file_path, content):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logging.info(f"Файл {file_path} успешно сохранён")
    except Exception as e:
        logging.error(f"Ошибка записи в {file_path}: {e}")

# Вспомогательные функции
def today_str():
    return datetime.now().strftime("%Y-%m-%d")

def is_expired(date_str):
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        return (datetime.now() - date) > timedelta(days=180)
    except ValueError:
        logging.error(f"Неверный формат даты: {date_str}")
        return True

async def get_promo_text():
    global last_promo_text
    content = await read_file(PROMO_FILE)
    last_promo_text = content.strip() if content.strip() else "Акции пока не добавлены."
    return last_promo_text

async def load_clients():
    global last_clients
    content = await read_file(DATA_FILE)
    clients = {}
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if not line.startswith("bonus:"):
            parts = line.split(",")
            if len(parts) >= 2:
                code = parts[0]
                clients[code] = {
                    "code": code,
                    "telegram_id": parts[1],
                    "bonuses": []
                }
        else:
            bonus_parts = line.split(":")
            if len(bonus_parts) == 3 and 'code' in locals():
                if not is_expired(bonus_parts[2]):
                    clients[code]["bonuses"].append({
                        "amount": int(bonus_parts[1]),
                        "date": bonus_parts[2]
                    })
        i += 1
    last_clients = clients
    return clients

async def save_clients(clients):
    global last_clients
    content = ''
    for client in clients.values():
        valid_bonuses = [b for b in client["bonuses"] if not is_expired(b["date"])]
        client["bonuses"] = valid_bonuses
        content += f"{client['code']},{client['telegram_id']}\n"
        for b in valid_bonuses:
            content += f"bonus:{b['amount']}:{b['date']}\n"
    await write_file(DATA_FILE, content)
    last_clients = clients

async def add_user_id(user_id):
    global last_users
    user_id = str(user_id)
    content = await read_file(USERS_FILE)
    users = set(content.splitlines())
    if user_id not in users:
        users.add(user_id)
        await write_file(USERS_FILE, "\n".join(users) + "\n")
        last_users = users
        logging.info(f"Добавлен user_id: {user_id}")

async def get_all_user_ids():
    global last_users
    content = await read_file(USERS_FILE)
    last_users = set(line.strip() for line in content.splitlines() if line.strip())
    return list(last_users)

async def is_code_used(code):
    global last_used_codes
    content = await read_file(USED_CODES_FILE)
    used = set(content.splitlines())
    last_used_codes = used
    return code in used

async def mark_code_used(code):
    global last_used_codes
    content = await read_file(USED_CODES_FILE)
    used = set(content.splitlines())
    used.add(code)
    await write_file(USED_CODES_FILE, "\n".join(used) + "\n")
    last_used_codes = used
    logging.info(f"Код {code} помечен как использованный")

def generate_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

def get_total_bonus(client):
    return sum(b["amount"] for b in client["bonuses"] if not is_expired(b["date"]))

async def is_referred_user(user_id):
    clients = await load_clients()
    return any(client["telegram_id"] == str(user_id) for client in clients.values())

# Клавиатуры
main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='📍 Как нас найти', callback_data='geo')],
    [InlineKeyboardButton(text='🎁 Бонусы', callback_data='bonus')],
    [InlineKeyboardButton(text='🔥 Текущие акции', callback_data='action')],
    [InlineKeyboardButton(text='❓ Частые вопросы (FAQ)', callback_data='faq')]
])

referred_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='💰 Мои бонусы', callback_data='check_bonus')],
    [InlineKeyboardButton(text='📜 Правила использования бонусов', callback_data='bonus_rules')],
    [InlineKeyboardButton(text='🛍 Сообщить о покупке', callback_data='shopping')],
    [InlineKeyboardButton(text='💸 Списать бонусы', callback_data='use_bonus')],
    [InlineKeyboardButton(text='🔑 Мой код', callback_data='show_code')],
    [InlineKeyboardButton(text='📩 Задать вопрос', callback_data='question')],
    [InlineKeyboardButton(text='📍 Как нас найти', callback_data='geo')],
    [InlineKeyboardButton(text='🔥 Текущие акции', callback_data='action')],
    [InlineKeyboardButton(text='❓ Частые вопросы (FAQ)', callback_data='faq')],
    [InlineKeyboardButton(text='🕰️ Интересные факты', callback_data='clock')]
])

bonus_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🆕 Зарегистрироваться', callback_data='registration')]
])

faq_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🕰️ Интересные факты', callback_data='clock')],
    [InlineKeyboardButton(text='🚚 Есть ли доставка?', callback_data='delivery')],
    [InlineKeyboardButton(text='🕒 График работы', callback_data='work')],
    [InlineKeyboardButton(text='🏬 Как найти магазин', callback_data='where')],
    [InlineKeyboardButton(text='⬅️ Назад', callback_data='back')]
])

admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='📢 Обновить акцию', callback_data='admin_update_promo')],
    [InlineKeyboardButton(text='🗑 Удалить акцию', callback_data='admin_delete_promo')],
    [InlineKeyboardButton(text='🔍 Проверить код', callback_data='admin_check_code')],
    [InlineKeyboardButton(text='📋 Список клиентов', callback_data='admin_list_clients')],
    [InlineKeyboardButton(text='📊 Статистика', callback_data='admin_stats')]
])

def get_confirm_keyboard(user_id, is_spend=False):
    prefix = "spend_" if is_spend else "confirm_"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"{prefix}{user_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")]
    ])

def get_reply_keyboard(user_id, message_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Ответить", callback_data=f"reply_{user_id}_{message_id}")]
    ])

# Обработчики
@dp.message(Command('start'))
async def welcome(message: Message):
    user_id = message.from_user.id
    await add_user_id(user_id)
    code = message.text.split()[-1] if len(message.text.split()) > 1 else None

    if code:
        if await is_code_used(code):
            await message.answer(
                "Эта реферальная ссылка уже использована. Обратитесь в магазин по адресу: проспект Генерала Острякова, 60.",
                parse_mode="HTML"
            )
            logging.warning(f"Попытка повторного использования кода: {code} пользователем {user_id}")
            return

        clients = await load_clients()
        if code in clients:
            await message.answer(
                "Вы уже зарегистрированы по этой ссылке.",
                parse_mode="HTML",
                reply_markup=referred_keyboard
            )
            return

        clients[code] = {
            'code': code,
            'telegram_id': str(user_id),
            'bonuses': [{'amount': 50, 'date': today_str()}]
        }
        await save_clients(clients)
        await mark_code_used(code)
        await message.answer(
            f"🎉 Вы зарегистрированы по реферальной ссылке!\n\n"
            f"Ваш код: {code}\n\n"
            f"Вам зачислено 50 бонусов за регистрацию! Используйте их на любой товар (до 50% стоимости).\n\n"
            f"Выберите, что вас интересует 👇",
            reply_markup=referred_keyboard,
            parse_mode="HTML"
        )
        logging.info(f"Регистрация user_id {user_id} по коду {code}, +50 бонусов")
    else:
        clients = await load_clients()
        if await is_referred_user(user_id):
            await message.answer(
                f"🎉 Добро пожаловать обратно в 'Час Ы'! ⌚\n\n"
                f"Вы уже зарегистрированы. Выберите, что вас интересует 👇",
                reply_markup=referred_keyboard,
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"🎉 Добро пожаловать в 'Час Ы'! ⌚\n\n"
                f"У нас самые лучшие часы в городе! 💎\n\n"
                f"Чтобы участвовать в программе лояльности, используйте реферальную ссылку из магазина.\n\n"
                f"Выберите, что вас интересует 👇",
                reply_markup=main_keyboard,
                parse_mode="HTML"
            )

@dp.message(Command('admin'))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Вы не админ.")
        return
    await message.answer("Админ-панель:", reply_markup=admin_keyboard)

@dp.callback_query(F.data == 'admin_update_promo')
async def admin_update_promo(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("Вы не админ.")
        return
    await callback.message.answer("Введите текст акции (например: Скидка 20% до 31 августа!):")
    user_context['waiting_for_promo'] = callback.from_user.id
    await callback.answer()

@dp.callback_query(F.data == 'admin_delete_promo')
async def admin_delete_promo(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("Вы не админ.")
        return
    try:
        global last_promo_text
        await write_file(PROMO_FILE, "Акции пока не добавлены.\n")
        last_promo_text = "Акции пока не добавлены."
        for uid in await get_all_user_ids():
            try:
                await bot.send_message(
                    uid,
                    f"📢 Текущая акция завершена!\nСледите за новыми акциями в нашем боте! 😊",
                    parse_mode="HTML",
                    reply_markup=referred_keyboard if await is_referred_user(int(uid)) else main_keyboard
                )
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление об удалении акции user_id {uid}: {e}")
        await callback.message.answer("Акция удалена! Пользователи уведомлены.", reply_markup=admin_keyboard)
        logging.info("Админ удалил акцию")
    except Exception as e:
        await callback.message.answer("Ошибка удаления акции.", reply_markup=admin_keyboard)
        logging.error(f"Ошибка удаления акции: {e}")
    await callback.answer()

@dp.message(lambda message: user_context.get('waiting_for_promo') == message.from_user.id)
async def process_promo(message: Message):
    user_context.pop('waiting_for_promo', None)
    if message.from_user.id != ADMIN_ID:
        await message.answer("Вы не админ.")
        return
    text = message.text.strip()
    if not text:
        await message.answer("Текст акции не может быть пустым.")
        return
    try:
        global last_promo_text
        await write_file(PROMO_FILE, text + "\n")
        last_promo_text = text
        for uid in await get_all_user_ids():
            try:
                await bot.send_message(
                    uid,
                    f"📢 У нас новая акция!\n\n{text}",
                    parse_mode="HTML",
                    reply_markup=referred_keyboard if await is_referred_user(int(uid)) else main_keyboard
                )
            except Exception as e:
                logging.error(f"Не удалось отправить акцию user_id {uid}: {e}")
        await message.answer("Акция обновлена!", reply_markup=admin_keyboard)
        logging.info(f"Админ обновил акцию: {text}")
    except Exception as e:
        await message.answer("Ошибка обновления акции.")
        logging.error(f"Ошибка обновления акции: {e}")

@dp.callback_query(F.data == 'admin_check_code')
async def admin_check_code(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("Вы не админ.")
        return
    await callback.message.answer("Введите код клиента:")
    user_context['waiting_for_code'] = callback.from_user.id
    await callback.answer()

@dp.message(lambda message: user_context.get('waiting_for_code') == message.from_user.id)
async def process_check_code(message: Message):
    user_context.pop('waiting_for_code', None)
    if message.from_user.id != ADMIN_ID:
        await message.answer("Вы не админ.")
        return
    code = message.text.strip()
    clients = await load_clients()
    if code in clients:
        total = get_total_bonus(clients[code])
        await message.answer(
            f"Для кода {code}:\nБонусов: {total}\nTelegram ID: {clients[code]['telegram_id']}",
            reply_markup=admin_keyboard
        )
    else:
        await message.answer("Код не найден.", reply_markup=admin_keyboard)

@dp.callback_query(F.data == 'admin_list_clients')
async def admin_list_clients(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("Вы не админ.")
        return
    clients = await load_clients()
    if not clients:
        await callback.message.answer("Нет клиентов.", reply_markup=admin_keyboard)
        return
    response = "Список клиентов:\n"
    for code, client in clients.items():
        total = get_total_bonus(client)
        response += f"Код: {code}, Бонусов: {total}, Telegram ID: {client['telegram_id']}\n"
    await callback.message.answer(response, reply_markup=admin_keyboard)
    await callback.answer()

@dp.callback_query(F.data == 'admin_stats')
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("Вы не админ.")
        return
    clients = await load_clients()
    users = await get_all_user_ids()
    total_bonuses = sum(get_total_bonus(client) for client in clients.values())
    response = (
        f"📊 Статистика:\n"
        f"Клиентов: {len(clients)}\n"
        f"Пользователей: {len(users)}\n"
        f"Общее количество бонусов: {total_bonuses}"
    )
    await callback.message.answer(response, reply_markup=admin_keyboard)
    await callback.answer()

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
    if await is_referred_user(callback.from_user.id):
        await callback.message.answer(
            f"Собирайте бонусы — 5% от каждой покупки часов. Тратьте на любой товар в магазине!",
            reply_markup=referred_keyboard,
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            f"Собирайте бонусы — 5% от каждой покупки часов. Тратьте на любой товар в магазине!\n\n"
            f"Чтобы начать, зарегистрируйтесь по реферальной ссылке из магазина.",
            reply_markup=bonus_keyboard,
            parse_mode="HTML"
        )
    await callback.answer()

@dp.callback_query(F.data == 'bonus_rules')
async def bonus_rules(callback: CallbackQuery):
    await callback.message.answer(
        "📜 Правила использования бонусов:\n"
        "- Бонусы начисляются в размере 5% от суммы покупки.\n"
        "- Бонусы можно использовать для оплаты до 50% стоимости товара.\n"
        "- Бонусы действительны 180 дней с даты начисления.\n"
        "- Для списания бонусов покажите ваш код в магазине.",
        parse_mode="HTML",
        reply_markup=referred_keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == 'registration')
async def registration_info(callback: CallbackQuery):
    await callback.message.answer(
        f"Чтобы зарегистрироваться, используйте реферальную ссылку из магазина.",
        parse_mode="HTML",
        reply_markup=main_keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == 'shopping')
async def ask_amount(callback: CallbackQuery):
    if not ADMIN_ID:
        await callback.message.answer(
            "Ошибка: админ не указан. Обратитесь в магазин по адресу: проспект Генерала Острякова, 60.",
            parse_mode="HTML"
        )
        logging.error("ADMIN_ID не указан")
        return
    if not await is_referred_user(callback.from_user.id):
        await callback.message.answer(
            "Вы не зарегистрированы. Используйте реферальную ссылку из магазина.",
            reply_markup=main_keyboard,
            parse_mode="HTML"
        )
        return
    await callback.message.answer(
        f"Введите сумму покупки в рублях (например: 8500) для начисления бонусов.",
        parse_mode="HTML"
    )
    user_context['waiting_for_purchase_amount'] = callback.from_user.id
    await callback.answer()

@dp.message(lambda message: user_context.get('waiting_for_purchase_amount') == message.from_user.id)
async def receive_purchase(message: Message):
    user_context.pop('waiting_for_purchase_amount', None)
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("Ошибка: введите положительное число (например, 8500).", reply_markup=referred_keyboard)
        return
    amount = int(message.text)
    if amount < 500:
        await message.answer("Сумма покупки слишком маленькая. Минимум - 500 руб.", reply_markup=referred_keyboard)
        return
    bonus = int(amount * 0.05)
    user_id = message.from_user.id
    pending_requests[user_id] = {
        'amount': amount,
        'bonus': bonus,
        'telegram_id': str(user_id)
    }
    await bot.send_message(
        ADMIN_ID,
        f"📢 Новая покупка!\nКлиент user_id {user_id}\nСумма: {amount} ₽\nБонусов к начислению: {bonus}",
        reply_markup=get_confirm_keyboard(user_id),
        parse_mode="HTML"
    )
    await message.answer("Заявка отправлена! Админ подтвердит бонусы.", reply_markup=referred_keyboard)

@dp.callback_query(F.data == "check_bonus")
async def check_bonus(callback: CallbackQuery):
    clients = await load_clients()
    user_id = str(callback.from_user.id)
    for data in clients.values():
        if data["telegram_id"] == user_id:
            total = get_total_bonus(data)
            expiring = sum(b["amount"] for b in data["bonuses"] if (datetime.now() - datetime.strptime(b["date"], "%Y-%m-%d")).days > 150)
            msg = f"У вас {total} бонусов."
            if expiring > 0:
                msg += f"\n⚠️ {expiring} бонусов истекут в течение 30 дней!"
            await callback.message.answer(msg, reply_markup=referred_keyboard)
            await callback.answer()
            return
    await callback.message.answer("Вы не зарегистрированы.", reply_markup=main_keyboard)

@dp.callback_query(F.data == 'use_bonus')
async def use_bonus(callback: CallbackQuery):
    if not ADMIN_ID:
        await callback.message.answer(
            "Ошибка: админ не указан. Обратитесь в магазин по адресу: проспект Генерала Острякова, 60.",
            parse_mode="HTML"
        )
        logging.error("ADMIN_ID не указан")
        return
    clients = await load_clients()
    user_id = str(callback.from_user.id)
    code = next((c for c, client in clients.items() if client["telegram_id"] == user_id), None)
    if not code:
        await callback.message.answer("Вы не зарегистрированы.", reply_markup=main_keyboard)
        return
    total = get_total_bonus(clients[code])
    if total == 0:
        await callback.message.answer("У вас нет бонусов.", reply_markup=referred_keyboard)
        return
    await callback.message.answer(
        f"У вас {total} бонусов. Введите сумму покупки (руб), чтобы запросить списание (до 50% стоимости). Показывайте код {code} в магазине для подтверждения."
    )
    user_context['waiting_for_use_bonus'] = user_id
    await callback.answer()

@dp.callback_query(F.data == 'show_code')
async def show_code(callback: CallbackQuery):
    clients = await load_clients()
    user_id = str(callback.from_user.id)
    code = next((c for c, client in clients.items() if client["telegram_id"] == user_id), None)
    if code:
        await callback.message.answer(f"Ваш код: {code}", reply_markup=referred_keyboard)
    else:
        await callback.message.answer("Вы не зарегистрированы.", reply_markup=main_keyboard)
    await callback.answer()

@dp.message(lambda message: user_context.get('waiting_for_use_bonus') == str(message.from_user.id))
async def process_use_bonus(message: Message):
    user_id = str(message.from_user.id)
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("Ошибка: введите положительное число (например, 8500).", reply_markup=referred_keyboard)
        user_context.pop('waiting_for_use_bonus', None)
        return
    amount = int(message.text)
    clients = await load_clients()
    code = next((c for c, client in clients.items() if client["telegram_id"] == user_id), None)
    if not code:
        await message.answer("Ошибка: код не найден.", reply_markup=main_keyboard)
        user_context.pop('waiting_for_use_bonus', None)
        return
    total_bonuses = get_total_bonus(clients[code])
    max_discount = amount // 2
    use_bonuses = min(total_bonuses, max_discount)
    if use_bonuses == 0:
        await message.answer("У вас недостаточно бонусов для списания.", reply_markup=referred_keyboard)
        user_context.pop('waiting_for_use_bonus', None)
        return
    remaining = total_bonuses - use_bonuses
    pending_spend_requests[user_id] = {
        'amount': amount,
        'use_bonuses': use_bonuses,
        'remaining': remaining,
        'code': code
    }
    await bot.send_message(
        ADMIN_ID,
        f"📢 Заявка на списание бонусов!\nКод: {code}\nСумма покупки: {amount} ₽\nСписать: {use_bonuses} (остаток: {remaining})\nПодтвердите, когда покупатель покажет код в магазине.",
        reply_markup=get_confirm_keyboard(user_id, is_spend=True),
        parse_mode="HTML"
    )
    await message.answer(f"Заявка отправлена! Админ подтвердит списание. Покажите код {code} в магазине.", reply_markup=referred_keyboard)
    user_context.pop('waiting_for_use_bonus', None)

@dp.callback_query(F.data.startswith('confirm_'))
async def confirm_purchase(callback: CallbackQuery):
    clients = await load_clients()
    user_id = int(callback.data.split('_')[1])
    if user_id not in pending_requests:
        await callback.message.edit_text("❌ Заявка не найдена")
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
        await save_clients(clients)
        await bot.send_message(
            user_id,
            f"🎉 Вам зачислено {bonus} бонусов!",
            parse_mode="HTML",
            reply_markup=referred_keyboard
        )
        await callback.message.edit_text("✅ Покупка подтверждена. Бонусы зачислены! 🎊")
        logging.info(f"Подтверждено начисление: user_id {user_id}, +{bonus} бонусов")
    else:
        await bot.send_message(
            user_id,
            "Ошибка: клиент не найден. Обратитесь в магазин по адресу: проспект Генерала Острякова, 60.",
            parse_mode="HTML",
            reply_markup=main_keyboard
        )
        await callback.message.edit_text("❌ Ошибка: клиент не найден")
        logging.error(f"Клиент user_id {user_id} не найден")
    del pending_requests[user_id]

@dp.callback_query(F.data.startswith('spend_'))
async def confirm_spend(callback: CallbackQuery):
    clients = await load_clients()
    user_id = int(callback.data.split('_')[1])
    if user_id not in pending_spend_requests:
        await callback.message.edit_text("❌ Заявка на списание не найдена")
        logging.error(f"Заявка на списание для user_id {user_id} не найдена")
        return

    code = pending_spend_requests[user_id]['code']
    client_found = None
    for c, client in clients.items():
        if client['telegram_id'] == str(user_id):
            client_found = client
            break

    if client_found:
        use_bonuses = pending_spend_requests[user_id]['use_bonuses']
        remaining = pending_spend_requests[user_id]['remaining']
        client_found['bonuses'] = []
        if remaining > 0:
            client_found['bonuses'].append({
                'amount': remaining,
                'date': today_str()
            })
        await save_clients(clients)
        await bot.send_message(
            user_id,
            f"✅ Вы использовали {use_bonuses} бонусов! Остаток: {remaining} бонусов.\n\n"
            f"Покажите код {code} в магазине для скидки.",
            parse_mode="HTML",
            reply_markup=referred_keyboard
        )
        await callback.message.edit_text("✅ Использование бонусов подтверждено! 🎊")
        logging.info(f"Подтверждено списание: код {code}, -{use_bonuses} бонусов, остаток {remaining}")
    else:
        await bot.send_message(
            user_id,
            "Ошибка: клиент не найден. Обратитесь в магазин по адресу: проспект Генерала Острякова, 60.",
            parse_mode="HTML",
            reply_markup=main_keyboard
        )
        await callback.message.edit_text("❌ Ошибка: клиент не найден")
        logging.error(f"Клиент user_id {user_id} не найден")
    del pending_spend_requests[user_id]

@dp.callback_query(F.data.startswith('reject_'))
async def reject_purchase(callback: CallbackQuery):
    user_id = int(callback.data.split('_')[1])
    if user_id in pending_requests:
        code = next((c for c, client in (await load_clients()).items() if client['telegram_id'] == str(user_id)), 'неизвестен')
        await bot.send_message(
            user_id,
            "К сожалению, покупка не подтверждена. Обратитесь в магазин по адресу: проспект Генерала Острякова, 60.",
            parse_mode="HTML",
            reply_markup=referred_keyboard
        )
        await callback.message.edit_text("❌ Покупка отклонена.")
        logging.info(f"Покупка для кода {code} отклонена")
        del pending_requests[user_id]
    elif user_id in pending_spend_requests:
        code = pending_spend_requests[user_id]['code']
        await bot.send_message(
            user_id,
            "К сожалению, использование бонусов не подтверждено. Обратитесь в магазин по адресу: проспект Генерала Острякова, 60.",
            parse_mode="HTML",
            reply_markup=referred_keyboard
        )
        await callback.message.edit_text("❌ Использование бонусов отклонено.")
        logging.info(f"Списание бонусов для кода {code} отклонено")
        del pending_spend_requests[user_id]
    else:
        await callback.message.edit_text("❌ Заявка не найдена")
        logging.error(f"Заявка для user_id {user_id} не найдена")

@dp.callback_query(F.data == "action")
async def action(callback: CallbackQuery):
    global last_promo_text
    try:
        current_promo = await get_promo_text()
        if last_promo_text == "Акции пока не добавлены.":
            last_promo_text = current_promo
            await callback.message.answer(current_promo, parse_mode="HTML")
        elif current_promo != last_promo_text:
            for uid in await get_all_user_ids():
                try:
                    await bot.send_message(
                        uid,
                        f"📢 У нас новая акция!\n\n{current_promo}",
                        parse_mode="HTML",
                        reply_markup=referred_keyboard if await is_referred_user(int(uid)) else main_keyboard
                    )
                except Exception as e:
                    logging.error(f"Не удалось отправить акцию user_id {uid}: {e}")
            last_promo_text = current_promo
            await callback.message.answer(current_promo, parse_mode="HTML")
        else:
            await callback.message.answer(current_promo, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка обработки акции: {e}")
        await callback.message.answer("Сейчас нет активных акций.", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == 'faq')
async def faq_question(callback: CallbackQuery):
    await callback.message.answer(
        "Задайте вопрос о нашем магазине или часах!",
        reply_markup=faq_keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == 'clock')
async def interesting_facts(callback: CallbackQuery):
    if not facts_for_clock:
        await callback.message.answer("Факты о часах временно недоступны.")
        logging.error("Список facts_for_clock пуст")
        await callback.answer()
        return
    fact = random.choice(facts_for_clock)
    await callback.message.answer(f"Интересный факт о часах:\n\n{fact}", parse_mode="HTML")
    keyboard = referred_keyboard if await is_referred_user(callback.from_user.id) else main_keyboard
    await callback.message.answer("Выберите, что вас интересует 👇", reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == 'delivery')
async def faq_delivery(callback: CallbackQuery):
    await callback.message.answer("Магазин \"Час Ы\" не предоставляет услугу доставки", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == 'work')
async def faq_qwork(callback: CallbackQuery):
    await callback.message.answer("Мы работаем ежедневно с 10:00 до 18:30", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "where")
async def faq_where(callback: CallbackQuery):
    await callback.message.answer(
        "Мы находимся в ТЦ \"Приветливый\" по адресу: проспект Генерала Острякова, 60.",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == 'question')
async def my_question(callback: CallbackQuery):
    if not ADMIN_ID:
        await callback.message.answer(
            "Ошибка: админ не указан. Обратитесь в магазин по адресу: проспект Генерала Острякова, 60.",
            parse_mode="HTML"
        )
        logging.error("ADMIN_ID не указан")
        return
    if not await is_referred_user(callback.from_user.id):
        await callback.message.answer(
            "Вы не зарегистрированы. Используйте реферальную ссылку из магазина.",
            reply_markup=main_keyboard,
            parse_mode="HTML"
        )
        return
    await callback.message.answer(
        f"📩 Вы можете задать любой вопрос.\n"
        "Напишите его здесь.\n"
        "Мы ответим в ближайшее время! ⏳",
        parse_mode="HTML"
    )
    user_context['waiting_for_question'] = callback.from_user.id
    await callback.answer()

@dp.message(lambda message: user_context.get('waiting_for_question') == message.from_user.id)
async def forward_question_to_admin(message: Message):
    user_id = message.from_user.id
    user_context.pop('waiting_for_question', None)
    try:
        forwarded = await bot.send_message(ADMIN_ID, message.text)
        await bot.send_message(
            ADMIN_ID,
            f"Вопрос от пользователя (user_id: {user_id}):",
            reply_markup=get_reply_keyboard(user_id, forwarded.message_id),
            parse_mode="HTML"
        )
        await message.answer(
            "Ваш вопрос отправлен! Мы ответим в ближайшее время.",
            parse_mode="HTML",
            reply_markup=referred_keyboard
        )
        logging.info(f"Вопрос от user_id {user_id} отправлен админу")
    except Exception as e:
        await message.answer(
            "Не удалось отправить вопрос. Обратитесь в магазин по адресу: проспект Генерала Острякова, 60.",
            parse_mode="HTML",
            reply_markup=referred_keyboard
        )
        logging.error(f"Ошибка отправки вопроса от user_id {user_id}: {e}")

@dp.message(lambda message: message.from_user.id == ADMIN_ID and user_context.get('waiting_for_admin_reply') is not None)
async def send_admin_reply(message: Message):
    user_id = user_context.pop('waiting_for_admin_reply', None)
    if user_id:
        if len(message.text) > 4096:
            await message.answer("Ошибка: ответ слишком длинный (максимум 4096 символов).", reply_markup=admin_keyboard)
            return
        try:
            await bot.send_message(
                user_id,
                message.text,
                parse_mode="HTML",
                reply_markup=referred_keyboard
            )
            await message.answer("Ответ отправлен пользователю.", reply_markup=admin_keyboard)
            logging.info(f"Ответ админа отправлен user_id {user_id}")
        except Exception as e:
            await message.answer("Не удалось отправить ответ пользователю.", reply_markup=admin_keyboard)
            logging.error(f"Ошибка отправки ответа user_id {user_id}: {e}")

@dp.callback_query(F.data.startswith('reply_'))
async def reply_to_user(callback: CallbackQuery):
    data = callback.data.split('_')
    user_id = int(data[1])
    await callback.message.answer(f"Напишите ответ для пользователя (user_id: {user_id}):", parse_mode="HTML")
    user_context['waiting_for_admin_reply'] = user_id
    await callback.answer()

@dp.callback_query(F.data == 'back')
async def back_to_menu(callback: CallbackQuery):
    keyboard = referred_keyboard if await is_referred_user(callback.from_user.id) else main_keyboard
    await callback.message.edit_text(
        "Выберите, что вас интересует 👇",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

async def main():
    init_files()
    logging.info("Бот 'Час Ы' запущен, данные хранятся в локальных файлах")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
