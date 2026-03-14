import telebot
import json
from telebot import types
from datetime import datetime
from dotenv import load_dotenv
import os
from pathlib import Path
from flask import Flask, request

# === Токен, публичный URL и админ ===
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL")  # пример: https://physicsofprocessbot-production.up.railway.app
ADMIN_ID = 381592065
SPB_PHONE = "+79899343367(Сбер)"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# === Каталог ===
catalog = [
    {"id": 1, "name": "Costa Rica Tarrazu\nРегион: Зона Лос-Сантоса\nРазновидность: Местная\nОбработка: Мытая\nОбжарка: Средняя\nВо вкусе: Косточковые, Шоколад, Карамель\nQ: 84.5\nЦена: 2.700₽",
     "photo": "https://static.tildacdn.com/tild3661-3139-4563-a631-653362343433/__1.jpeg", "price": 2700},
    {"id": 2, "name": "Fruto De Lobo 3.0\nРегион: Уила, Нориньо, Толима\nОбработка: Мытая\nОбжарка: Средняя\nАрабика: 40%, Робуста: 60%\nВо вкусе: Шоколад, Карамель, Изюм\nЦена: 1.800₽",
     "photo": "https://ibb.co/Tx6fhR2c", "price": 1800},
    {"id": 3, "name": "Colombia Excelso\nРегион: Антиокия\nРазновидность: Местная\nОбработка: Мытая\nОбжарка: Средняя\nВо вкусе: Цитрусы, Карамель, Красные ягоды\nQ: 84.5\nЦена: 2.400₽",
     "photo": "https://ibb.co/My77rB40", "price": 2400},
    {"id": 4, "name": "Brazil Santos\nРегион: Сантос\nРазновидность: Various\nОбработка: Натуральная\nОбжарка: Средняя\nВо вкусе: Орехи, Карамель, Шоколад\nQ: 83\nЦена: 2.200₽",
     "photo": "https://ibb.co/BVwj4D9d", "price": 2200},
    {"id": 5, "name": "Brazil Conilon\nРегион: Montanhas do Espirito Santo\nОбработка: Полумытая(CD)\nОбжарка: Средняя\nВо вкусе: Нутелла, Орех, Темный шоколад\nQ: 83\nЦена: 2.200₽",
     "photo": "https://static.tildacdn.com/tild3266-3464-4035-a666-653438613539/WhatsApp_Image_2026-.jpeg", "price": 2200},
]

# === Файл для хранения данных ===
DATA_FILE = Path(__file__).resolve().parent / "data.json"

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"carts": {}, "user_positions": {}, "user_steps": {}, "user_temp_data": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

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
    chat_id = str(message.chat.id)
    data = load_data()
    data["user_positions"][chat_id] = 0
    save_data(data)
    bot.send_message(chat_id, f"{get_greeting()} Чтобы заказать кофе, воспользуйтесь меню ниже",
                     reply_markup=main_menu())

# === Каталог ===
@bot.message_handler(func=lambda m: m.text == "Каталог")
def show_catalog(message):
    chat_id = str(message.chat.id)
    data = load_data()
    data["user_positions"][chat_id] = 0
    save_data(data)
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

# === Callback для каталога и корзины ===
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = str(call.message.chat.id)
    data = load_data()
    data_call = call.data

    if data_call.startswith("prev_"):
        idx = int(data_call.split("_")[1]) - 1
        send_catalog_item(chat_id, idx)
    elif data_call.startswith("next_"):
        idx = int(data_call.split("_")[1]) + 1
        send_catalog_item(chat_id, idx)
    elif data_call.startswith("add_"):
        idx = int(data_call.split("_")[1])
        item = catalog[idx]
        bot.send_message(chat_id, f"Укажите количество для «{item['name'].splitlines()[0]}»:")
        bot.register_next_step_handler(call.message, process_quantity, item_id=item["id"])
        bot.answer_callback_query(call.id)
    elif data_call == "clear_confirm":
        data["carts"][chat_id] = []
        save_data(data)
        bot.send_message(chat_id, "Корзина очищена.", reply_markup=main_menu())
        bot.answer_callback_query(call.id, "Корзина очищена!")
    elif data_call == "clear_cancel":
        bot.send_message(chat_id, "Отменено. Корзина сохранена.", reply_markup=main_menu())
        bot.answer_callback_query(call.id, "Отмена очистки")
    else:
        bot.answer_callback_query(call.id)

# === Добавление товара в корзину ===
def process_quantity(message, item_id):
    chat_id = str(message.chat.id)
    data = load_data()
    carts = data.setdefault("carts", {})

    text = message.text.strip()
    if not text.isdigit():
        bot.send_message(chat_id, "Введите целое число.")
        bot.register_next_step_handler(message, process_quantity, item_id)
        return

    qty = int(text)
    item = next((i for i in catalog if i["id"] == item_id), None)
    if not item:
        bot.send_message(chat_id, "Ошибка: товар не найден.")
        return

    total = item["price"] * qty
    cart_list = carts.setdefault(chat_id, [])
    existing = next((e for e in cart_list if e["item_id"] == item_id), None)
    if existing:
        existing["qty"] += qty
        existing["total"] += total
    else:
        cart_list.append({"item_id": item_id, "qty": qty, "total": total})

    save_data(data)
    bot.send_message(chat_id,
                     f"Добавлено в корзину: {item['name'].splitlines()[0]} × {qty} = {total}₽",
                     reply_markup=main_menu())

# === Корзина ===
@bot.message_handler(func=lambda m: m.text == "Корзина")
def handle_cart(message):
    chat_id = str(message.chat.id)
    data = load_data()
    cart = data.get("carts", {}).get(chat_id, [])

    if not cart:
        bot.send_message(chat_id, "Корзина пуста", reply_markup=main_menu())
        return

    text = "*Ваша корзина:*\n\n"
    total_sum = 0
    for entry in cart:
        item = next((i for i in catalog if i["id"] == entry["item_id"]), None)
        if item:
            total_sum += entry["total"]
            text += f"{item['name'].splitlines()[0]} — {entry['qty']} шт. × {item['price']}₽ = {entry['total']}₽\n"
    text += f"\n*Итого:* {total_sum}₽"
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=main_menu())

# === Очистка корзины ===
@bot.message_handler(func=lambda m: m.text == "Очистить корзину")
def handle_clear_cart(message):
    chat_id = str(message.chat.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Да, очистить", callback_data="clear_confirm"))
    markup.add(types.InlineKeyboardButton("Нет, отмена", callback_data="clear_cancel"))
    bot.send_message(chat_id, "Вы уверены, что хотите очистить корзину?", reply_markup=markup)

# === Оптовые цены ===
@bot.message_handler(func=lambda m: m.text == "Оптовые цены")
def handle_wholesale(message):
    chat_id = message.chat.id
    pdf_path = "opt_prices.pdf"
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            bot.send_document(chat_id, f, caption="Наш прайс для оптовиков")
    else:
        bot.send_message(chat_id, "Файл с оптовыми ценами пока не найден.", reply_markup=main_menu())

# === Оформление заказа (имя → телефон → адрес) ===
@bot.message_handler(func=lambda m: m.text == "Оформить заказ")
def handle_checkout(message):
    chat_id = str(message.chat.id)
    bot.send_message(chat_id, "Введите ваше имя:")
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    chat_id = str(message.chat.id)
    data = load_data()
    temp = data.setdefault("user_temp_data", {})
    temp.setdefault(chat_id, {})["name"] = message.text.strip()
    save_data(data)
    bot.send_message(chat_id, "Введите ваш номер телефона:")
    bot.register_next_step_handler(message, get_phone)

def get_phone(message):
    chat_id = str(message.chat.id)
    data = load_data()
    temp = data["user_temp_data"]
    temp[chat_id]["phone"] = message.text.strip()
    save_data(data)
    bot.send_message(chat_id, "Введите ваш адрес:")
    bot.register_next_step_handler(message, get_address)

def get_address(message):
    chat_id = str(message.chat.id)
    data = load_data()
    temp = data["user_temp_data"]
    temp[chat_id]["address"] = message.text.strip()
    save_data(data)
    send_order(chat_id)  # отправляем пользователю и админу

def send_order(chat_id):
    data = load_data()
    cart = data.get("carts", {}).get(chat_id, [])
    temp = data.get("user_temp_data", {}).get(chat_id, {})

    if not cart:
        bot.send_message(chat_id, "Корзина пуста", reply_markup=main_menu())
        return

    # Формируем текст заказа
    text = "*Новый заказ:*\n\n"
    for entry in cart:
        item = next((i for i in catalog if i["id"] == entry["item_id"]), None)
        if item:
            text += f"{item['name'].splitlines()[0]} — {entry['qty']} шт. × {item['price']}₽ = {entry['total']}₽\n"
    total_sum = sum(entry["total"] for entry in cart)
    text += f"\n*Итого:* {total_sum}₽\n\n"
    text += f"Имя: {temp.get('name','')}\nТелефон: {temp.get('phone','')}\nАдрес: {temp.get('address','')}"

    # Сообщение пользователю
    bot.send_message(chat_id,
                     f"Спасибо за заказ! Оплатите через СБП:\n{SPB_PHONE}\nПосле оплаты отправьте скриншот.",
                     reply_markup=main_menu())

    # Сообщение админу
    bot.send_message(ADMIN_ID, text)

# === Webhook Flask ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{PUBLIC_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))