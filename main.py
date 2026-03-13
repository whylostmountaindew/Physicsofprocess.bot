import telebot
from telebot import types
from datetime import datetime
from dotenv import load_dotenv
import os
from pathlib import Path  #для работы с путями

# === Токен ===
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# === СБП ===
SPB_PHONE = "+79899343367(Сбер)"  # номер для перевода
SPB_QR = "https://ibb.co/TBPrsjBQ"  # ссылка на QR-код (можно прямую на картинку)

# === Админ ===
ADMIN_ID = 5314523287

# === Каталог ===
catalog = [
    {"id": 1,
     "name": "Costa Rica Tarrazu\nРегион: Зона Лос-Сантоса\nРазновидность: Местная\nОбработка: Мытая\nОбжарка: Средняя\nВо вкусе: Косточковые, Шоколад, Карамель\nQ: 84.5\nЦена: 2.700₽",
     "photo": "https://static.tildacdn.com/tild3661-3139-4563-a631-653362343433/__1.jpeg", "price": 2700},
    {"id": 2,
     "name": "Fruto De Lobo 3.0\nРегион: Уила, Нориньо, Толима\nОбработка: Мытая\nОбжарка: Средняя\nАрабика: 40%, Робуста: 60%\nВо вкусе: Шоколад, Карамель, Изюм\nЦена: 1.800₽",
     "photo": "https://ibb.co/Tx6fhR2c", "price": 1800},
    {"id": 3,
     "name": "Colombia Excelso\nРегион: Антиокия\nРазновидность: Местная\nОбработка: Мытая\nОбжарка: Средняя\nВо вкусе: Цитрусы, Карамель, Красные ягоды\nQ: 84.5\nЦена: 2.400₽",
     "photo": "https://ibb.co/My77rB40", "price": 2400},
    {"id": 4,
     "name": "Brazil Santos\nРегион: Сантос\nРазновидность: Various\nОбработка: Натуральная\nОбжарка: Средняя\nВо вкусе: Орехи, Карамель, Шоколад\nQ: 83\nЦена: 2.200₽",
     "photo": "https://ibb.co/BVwj4D9d", "price": 2200},
    {"id": 5,
     "name": "Brazil Conilon\nРегион: Montanhas do Espirito Santo\nОбработка: Полумытая(CD)\nОбжарка: Средняя\nВо вкусе: Нутелла, Орех, Темный шоколад\nQ: 83\nЦена: 2.200₽",
     "photo": "https://static.tildacdn.com/tild3266-3464-4035-a666-653438613539/WhatsApp_Image_2026-.jpeg", "price": 2200},
]

# === Хранилища ===
carts = {}  # chat_id → список товаров
user_positions = {}  # chat_id → индекс в каталоге
user_steps = {}  # chat_id → этап ("address", "phone")
user_temp_data = {}  # chat_id → {address, phone}

# === Вспомогательные функции ===
def get_greeting():
    hour = datetime.now().hour
    if 0 <= hour < 6:
        return "Доброй ночи!"
    elif 6 <= hour < 12:
        return "Доброе утро!"
    elif 12 <= hour < 18:
        return "Добрый день!"
    else:
        return "Добрый вечер!"

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Каталог", "Корзина")
    markup.add("Оформить заказ", "Очистить корзину")
    markup.add("Оптовые цены")
    return markup

# === /start ===
@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    user_positions[chat_id] = 0
    bot.send_message(chat_id, f"{get_greeting()} Чтобы заказать кофе, воспользуйтесь меню ниже",
                     reply_markup=main_menu())

# === Каталог ===
@bot.message_handler(func=lambda m: m.text == "Каталог")
def show_catalog(message):
    chat_id = message.chat.id
    user_positions[chat_id] = 0
    send_catalog_item(chat_id, 0)

def send_catalog_item(chat_id, index):
    if index < 0 or index >= len(catalog):
        bot.send_message(chat_id, "Нет такого товара.")
        return

    item = catalog[index]
    markup = types.InlineKeyboardMarkup()
    if index > 0:
        markup.add(types.InlineKeyboardButton("<<< Пред", callback_data=f"prev_{index}"))
    markup.add(types.InlineKeyboardButton("Добавить в корзину", callback_data=f"add_{index}"))
    if index < len(catalog) - 1:
        markup.add(types.InlineKeyboardButton("След >>>", callback_data=f"next_{index}"))

    bot.send_photo(chat_id, item["photo"], caption=item["name"], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data = call.data

    if data.startswith("prev_"):
        idx = int(data.split("_")[1]) - 1
        send_catalog_item(chat_id, idx)

    elif data.startswith("next_"):
        idx = int(data.split("_")[1]) + 1
        send_catalog_item(chat_id, idx)

    elif data.startswith("add_"):
        idx = int(data.split("_")[1])
        item = catalog[idx]
        bot.send_message(chat_id, f"Укажите количество для «{item['name'].splitlines()[0]}»:")
        bot.register_next_step_handler_by_chat_id(chat_id, process_quantity, item_id=item["id"])

    elif data == "clear_confirm":
        carts[chat_id] = []
        bot.send_message(chat_id, "Корзина очищена.", reply_markup=main_menu())
        bot.answer_callback_query(call.id, "Корзина очищена!")

    elif data == "clear_cancel":
        bot.send_message(chat_id, "Отменено. Корзина сохранена.", reply_markup=main_menu())
        bot.answer_callback_query(call.id, "Отмена очистки.")

    bot.answer_callback_query(call.id)

def process_quantity(message, item_id):
    chat_id = message.chat.id
    text = message.text.strip()

    if not text.isdigit():
        bot.send_message(chat_id, "Введите целое число.")
        bot.register_next_step_handler_by_chat_id(chat_id, process_quantity, item_id=item_id)
        return

    qty = int(text)
    item = next((i for i in catalog if i["id"] == item_id), None)
    if not item:
        bot.send_message(chat_id, "Ошибка: товар не найден.")
        return

    total = item["price"] * qty
    carts.setdefault(chat_id, []).append({"item_id": item_id, "qty": qty, "total": total})

    bot.send_message(chat_id,
                     f"Добавлено в корзину: {item['name'].splitlines()[0]} × {qty} = {total:,}₽".replace(",", " "),
                     reply_markup=main_menu())

# === Оптовые цены ===
@bot.message_handler(func=lambda m: m.text == "Оптовые цены")
def send_wholesale_prices(message):
    chat_id = message.chat.id
    pdf_path = Path(__file__).resolve().parent / "opt_prices.pdf"

    if pdf_path.exists():
        with open(pdf_path, "rb") as file:
            bot.send_document(
                chat_id,
                file,
                caption="Актуальные оптовые цены. Для сотрудничества свяжитесь с нами."
            )
    else:
        bot.send_message(chat_id, "Файл с оптовыми ценами временно недоступен.")

# === Корзина ===
@bot.message_handler(func=lambda m: m.text == "Корзина")
def handle_cart(message):
    chat_id = message.chat.id
    cart = carts.get(chat_id, [])
    if not cart:
        bot.send_message(chat_id, "Корзина пуста")
        return

    text = "*Ваша корзина:*\n\n"
    total_sum = 0
    for entry in cart:
        item = next((i for i in catalog if i["id"] == entry["item_id"]), None)
        if item:
            total_sum += entry["total"]
            text += f"{item['name'].splitlines()[0]} — {entry['qty']} шт. × {item['price']}₽ = {entry['total']:,}₽\n"
    text += f"\n*Итого:* {total_sum:,}₽".replace(",", " ")
    bot.send_message(chat_id, text, parse_mode="Markdown")

# === Остальной код (очистка корзины, оформление заказа, приём чеков) остаётся без изменений ===

# === Запуск ===
if __name__ == "__main__":
    bot.infinity_polling()