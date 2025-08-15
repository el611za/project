Telegram Bot "Час Ы"
Бот для магазина часов "Час Ы" (@Chas_bl_bot). Реализует:

Программу лояльности: регистрация по реферальным ссылкам, начисление бонусов (5% от покупки), использование бонусов (до 50% стоимости).
Интерактивное меню с FAQ, включая факты о часах (🕰️).
Отправку акций и вопросов администратору.

Как использовать

Запустите бота: @Chas_bl_bot /start.
Для регистрации используйте реферальную ссылку из магазина.
Проверяйте бонусы, задавайте вопросы или узнавайте факты о часах.

Установка

Клонируйте репозиторий: git clone https://github.com/el611za/project.git.
Установите зависимости: pip install -r requirements.txt.
Запустите: python clockbot.py.

Деплой на Render

Создайте сервис на Render (Python, Web Service).
Укажите репозиторий: https://github.com/el611za/project.
Настройте переменные окружения: PYTHON_VERSION=3.13, BOT_TOKEN=your_token, NUM_LINKS=10.
Настройте диск: Mount Path /opt/render/project/data, Size 1 GB.
Build Command: pip install -r requirements.txt.
Start Command (для бота): python clockbot.py.
Start Command (для генератора ссылок): python generate_referrals.py.

Файлы

clockbot.py: Основной код бота.
generate_referrals.py: Генерация реферальных ссылок.
requirements.txt: Зависимости.
.gitignore: Игнорирование данных файлов.
README.md: Описание проекта.

Стек

Python 3.13
aiogram 3.21.0
requests 2.32.4
