import random
import string
import os
from aiogram import Bot

API_TOKEN = os.getenv('BOT_TOKEN', '8130975273:AAE6GDAcZsmUCTQOJ3kfim0680SPYtAnmVQ')
ADMIN_ID = 50371663
bot = Bot(token=API_TOKEN)

def generate_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

def generate_referral_links(num_links):
    links = []
    for _ in range(num_links):
        token = generate_token()
        link = f"t.me/Chas_bl_bot?start={token}"
        links.append(link)
    return links

async def send_links_to_admin(links):
    await bot.send_message(ADMIN_ID, "Сгенерированы реферальные ссылки:\n" + "\n".join(links))

if __name__ == "__main__":
    import asyncio
    num_links = int(os.getenv('NUM_LINKS', 10))
    links = generate_referral_links(num_links)
    os.makedirs(os.path.dirname("/opt/render/project/data/referral_links.txt"), exist_ok=True)
    with open("/opt/render/project/data/referral_links.txt", "w", encoding="utf-8") as f:
        for link in links:
            f.write(link + "\n")
    print(f"Сгенерировано {num_links} ссылок, сохранено в referral_links.txt")
    asyncio.run(send_links_to_admin(links))
