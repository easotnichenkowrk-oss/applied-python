import asyncio
import logging
import sys
import json
import os
from datetime import datetime, timedelta
from io import BytesIO
import pandas as pd
import matplotlib.pyplot as plt
import requests
from PIL import Image
from pyzbar.pyzbar import decode as decode_barcode
from aiogram import Bot, Dispatcher, F
from aiogram.types import (Message, CallbackQuery, ContentType, BufferedInputFile,
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter, CommandStart, Command
import asyncio
import threading
from keepalive import run_web
import random

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден!")

bot = Bot(BOT_TOKEN)


sys.stdout.reconfigure(line_buffering=True)
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(name)s: %(message)s')

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

class ProfileForm(StatesGroup):
    weight = State()
    height = State()
    age = State()
    gender = State()
    city = State()

class FoodForm(StatesGroup):
    food_name = State()
    food_barcode = State()
    food_photo = State()
    food_weight = State()

class WaterForm(StatesGroup):
    water_amount = State()

class WorkoutForm(StatesGroup):
    search_query = State()
    select_type = State()
    duration = State()

def main_menu():
    # Теперь Профиль — это центральная кнопка на главной
    kb = [
        [InlineKeyboardButton(text="👤 Профиль", callback_data="menu_profile")],
        [InlineKeyboardButton(text="🍽 Еда", callback_data="menu_food"),
         InlineKeyboardButton(text="💧 Вода", callback_data="menu_water")],
        [InlineKeyboardButton(text="💪 Тренировка", callback_data="menu_workout")],
        [InlineKeyboardButton(text="📊 Цели и Прогресс", callback_data="menu_goal"),
         InlineKeyboardButton(text="📈 Графики", callback_data="menu_visualization")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def profile_settings_kb():
    # Клавиатура внутри раздела "Профиль"
    kb = [
        [InlineKeyboardButton(text="📝 Редактировать 'Обо мне'", callback_data="start_form")],
        [InlineKeyboardButton(text="🎯 Выбрать цель", callback_data="setup_goal")],
        [InlineKeyboardButton(text="💡 Получить совет", callback_data="get_advice")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def goal_selection_kb():
    # Выбор цели
    kb = [
        [InlineKeyboardButton(text="📉 Сбросить вес", callback_data="set_goal_lose")],
        [InlineKeyboardButton(text="⚖️ Поддержать вес", callback_data="set_goal_keep")],
        [InlineKeyboardButton(text="📈 Набрать вес", callback_data="set_goal_gain")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def start_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Создать профиль", callback_data="start_form")]
    ])

def profile_kb(user_data):
    # Эта функция нужна для работы формы "Обо мне"
    w = user_data.get("weight", "—")
    h = user_data.get("height", "—")
    a = user_data.get("age", "—")
    g_raw = user_data.get("gender", "—")
    g = "М" if g_raw == "Male" else ("Ж" if g_raw == "Female" else "—")
    c = user_data.get("city", "—")
    
    kb = [
        [InlineKeyboardButton(text=f"⚖ Вес: {w}", callback_data="edit_weight"),
         InlineKeyboardButton(text=f"📏 Рост: {h}", callback_data="edit_height")],
        [InlineKeyboardButton(text=f"🎂 Возраст: {a}", callback_data="edit_age"),
         InlineKeyboardButton(text=f"⚧ Пол: {g}", callback_data="edit_gender")],
        [InlineKeyboardButton(text=f"🌍 Город: {c}", callback_data="edit_city")],
        [InlineKeyboardButton(text="✅ Готово", callback_data="menu_profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
def gender_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Мужской", callback_data="gender_Male"),
         InlineKeyboardButton(text="Женский", callback_data="gender_Female")]
    ])

def water_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💧 +250 мл", callback_data="water_add_250"),
            InlineKeyboardButton(text="📝 Ввести свое", callback_data="water_add")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")] # Добавлены скобки []
    ])

def food_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Поиск названия", callback_data="food_by_name")],
        [InlineKeyboardButton(text="🔢 Ввести штрихкод", callback_data="food_by_barcode")],
        [InlineKeyboardButton(text="📷 Фото штрихкода", callback_data="food_by_photo")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])

def workout_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏃 Выбрать тренировку", callback_data="workout_start")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])

def workout_select_kb(candidates):
    buttons = []
    for idx, name in candidates:
        short_name = (name[:30] + '..') if len(name) > 30 else name
        buttons.append([InlineKeyboardButton(text=short_name, callback_data=f"sel_work_{idx}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

class FoodAPI:
    def search_food(self, query):
        # OpenFoodFacts требует корректный User-Agent
        headers = {'User-Agent': 'FitnessCoachBot/1.0'}
        # Добавляем фильтр по полям, чтобы ускорить ответ
        url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&fields=product_name,nutriments"
        try:
            resp = requests.get(url, headers=headers, timeout=15).json()
            products = resp.get('products', [])
            
            if products:
                for p in products:
                    nutr = p.get('nutriments', {})
                    kcal = nutr.get('energy-kcal_100g') or nutr.get('energy-kcal_value') or nutr.get('energy-kcal')
                    
                    if kcal:
                        return {
                            "foods": {
                                "food": [{
                                    "name": p.get('product_name', 'Unknown Product'), 
                                    "calories": float(kcal), 
                                    "serving_weight": 100
                                }]
                            }
                        }
        except Exception as e:
            logging.error(f"Search API Error: {e}")
        return {}

    def get_by_barcode(self, code):
        headers = {'User-Agent': 'MyFitnessBot/1.0'}
        url = f"https://world.openfoodfacts.org/api/v0/product/{code}.json"
        try:
            resp = requests.get(url, headers=headers, timeout=5).json()
            if resp.get('status') == 1:
                p = resp['product']
                nutriments = p.get('nutriments', {})
                kcal = nutriments.get('energy-kcal_100g') or nutriments.get('energy-kcal') or 0
                return {"food": {"name": p.get('product_name', 'Unknown'), "calories": float(kcal), "serving_weight": 100}}
        except Exception as e:
            logging.error(f"Barcode API Error: {e}")
        return {"food": {"name": "Unknown"}}

def goal_menu(uid, rem_data):
    kb = [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

async def get_temp_for_city(city):
    api = 'ca1bec131fe374faa70dec2ead03b0b6'
    url = 'https://api.openweathermap.org/data/2.5/weather'
    params = {'q': city, 'appid': api, 'units': 'metric'}
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            api_data = response.json()
            return api_data['main']['temp']
    except Exception as e:
        logging.error(f"Weather error: {e}")
    return 20


excercise_dataset = "exercise_dataset.csv"
user_data_store = "users.json"
user_db = {}

def initialize_exercise_db():
    try:
        df = pd.read_csv(excercise_dataset)
        target_col = 'Activity, Exercise or Sport (1 hour)'
        if target_col in df.columns:
            df = df.dropna(subset=[target_col])
            df['search_index'] = df[target_col].str.lower()
        return df
    except Exception as e:
        logging.error(f"❌ Ошибка при чтении CSV: {e}")
        return pd.DataFrame()

exercise_data = initialize_exercise_db()

def persist_user_data():
    try:
        with open(user_data_store, "w", encoding="utf-8") as f:
            json.dump(user_db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Save error: {e}")

def retrieve_user_data():
    global user_db
    if os.path.exists(user_data_store):
        try:
            with open(user_data_store, "r", encoding="utf-8") as f:
                user_db = json.load(f)
        except Exception as e:
            logging.error(f"Load error: {e}")
            user_db = {}
    else:
        user_db = {}

retrieve_user_data()


PROFILE_HINTS = {"weight": "⚖ <b>Вес (кг)</b>\nВведи целое число, например: <i>70</i>",
    "height": "📏 <b>Рост (см)</b>\nВведи целое число, например: <i>175</i>",
    "age": "🎂 <b>Возраст</b>\nВведи полные года, например: <i>30</i>",
    "city": "🌍 <b>Город</b>\nНужен для учета водного баланса (англ., только буквы)",
    "gender": "⚧ <b>Пол</b>\nВлияет на формулу нормы калорий"}

async def derive_daily_metrics(uid):
    user_key = str(uid)
    profile = user_db.get(user_key, {})
    
    w = profile.get("weight", 70)
    h = profile.get("height", 170)
    a = profile.get("age", 25)
    g = profile.get("gender", "Male")
    goal = profile.get("goal", "keep")
    city = profile.get("city", "Moscow")
    
    # Расчет BMR
    base_bmr = 10 * w + 6.25 * h - 5 * a
    bmr = base_bmr - 161 if g == "Female" else base_bmr + 5
    
    # Учет цели
    if goal == "lose":
        cal_target = int(bmr * 1.2 * 0.85)
    elif goal == "gain":
        cal_target = int(bmr * 1.2 * 1.15)
    else:
        cal_target = int(bmr * 1.2)
        
    # Вода (без изменений)
    current_temp = await get_temp_for_city(city)
    water_weather_bonus = 500 if current_temp > 25 else 0
    today_iso = datetime.now().strftime("%Y-%m-%d")
    todays_workouts = [item for item in profile.get("workouts", []) if item["date"].startswith(today_iso)]
    total_minutes = sum(x["duration"] for x in todays_workouts)
    water_activity_bonus = (total_minutes // 30) * 500
    final_water_target = int(w * 30 + water_weather_bonus + water_activity_bonus)
    
    # Текущие показатели
    todays_water_logs = [log for log in profile.get("water_log", []) if log["timestamp"].startswith(today_iso)]
    water_consumed = sum(log["amount"] for log in todays_water_logs)
    calories_burned = sum(x["kcal"] for x in todays_workouts)
    
    return {
        "cal_target": cal_target,
        "cal_burned": calories_burned,
        "water_target": final_water_target,
        "water_current": water_consumed,
        "goal": goal
    }

async def refresh_profile_ui(message: Message, user_id: str):
    try:
        pid = user_db[user_id].get("profile_msg_id")
        text_header = "👤 <b>Обо мне:</b>"
        if pid:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=pid,
                text=text_header,
                reply_markup=profile_kb(user_db[user_id]),
                parse_mode="HTML"
            )
        else:
            raise ValueError("No message ID")
    except Exception:
        new_msg = await message.answer(
            "👤 <b>Обо мне:</b>",
            reply_markup=profile_kb(user_db[user_id]),
            parse_mode="HTML"
        )
        user_db[user_id]["profile_msg_id"] = new_msg.message_id
        persist_user_data()

# === HANDLERS ===

@dp.message(CommandStart())
async def cmd_launch(message: Message):
    await message.answer(
        "👋 Привет! Я твой трекер здоровья..\nЗаполни раздел 'Обо мне', чтобы получить рассчеты.",
        reply_markup=start_kb()
    )

@dp.callback_query(F.data == "start_form")
async def profile_setup_start(cb: CallbackQuery):
    uid = str(cb.from_user.id)
    if uid not in user_db:
        user_db[uid] = {
            "weight": 70, "height": 170, "age": 25, # Defaults to avoid crash
            "gender": "Male", "city": "Moscow", 
            "workouts": [], "water_log": [], "food_log": []
        }
    
    msg = await cb.message.edit_text(
        "👤 <b>Обо мне:</b>", 
        reply_markup=profile_kb(user_db[uid]),
        parse_mode="HTML"
    )
    user_db[uid]["profile_msg_id"] = msg.message_id
    persist_user_data()

@dp.callback_query(F.data == "back_to_menu")
async def navigate_main(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("🏠 Главное меню:\n Для возвращения в это меню ты всегда можешь использовать команду /main_menu", reply_markup=main_menu())

@dp.message(Command(commands=["main_menu"]))
async def cmd_main_menu(message: Message):
    await message.answer("🏠 Главное меню:\n Для возвращения в это меню ты всегда можешь использовать команду /main_menu", reply_markup=main_menu())

@dp.callback_query(F.data.startswith("edit_"))
async def profile_edit_trigger(cb: CallbackQuery, state: FSMContext):
    field_key = cb.data.split("_")[1]
    await state.update_data(editing_field=field_key)
    
    if field_key == "gender":
        await cb.message.answer(PROFILE_HINTS["gender"], reply_markup=gender_kb(), parse_mode="HTML")
        await state.set_state(ProfileForm.gender)
    else:
        mapper = {
            "weight": ProfileForm.weight, "height": ProfileForm.height,
            "age": ProfileForm.age, "city": ProfileForm.city
        }
        await state.set_state(mapper.get(field_key))
        prompt_msg = await cb.message.answer(PROFILE_HINTS.get(field_key, "Введи значение:"), parse_mode="HTML")
        await state.update_data(prompt_id=prompt_msg.message_id)

@dp.callback_query(StateFilter(ProfileForm.gender), F.data.startswith("gender_"))
async def profile_gender_selection(cb: CallbackQuery, state: FSMContext):
    val = cb.data.split("_")[1]
    uid = str(cb.from_user.id)
    user_db[uid]["gender"] = val
    persist_user_data()
    try: await cb.message.delete() 
    except: pass
    await refresh_profile_ui(cb.message, uid)
    await state.clear()

@dp.message(StateFilter(ProfileForm.weight, ProfileForm.height, ProfileForm.age, ProfileForm.city))
async def profile_store_value(msg: Message, state: FSMContext):
    uid = str(msg.from_user.id)
    ctx_data = await state.get_data()
    field = ctx_data.get("editing_field")
    raw_text = msg.text.strip()
    
    try:
        if field == "weight":
            val = float(raw_text.replace(",", "."))
            if not (20 <= val <= 350): raise ValueError
            user_db[uid][field] = val
        elif field == "height":
            val = int(raw_text)
            user_db[uid][field] = val
        elif field == "age":
            val = int(raw_text)
            user_db[uid][field] = val
        elif field == "city":
            if not raw_text.replace("-", "").isalpha(): raise ValueError
            user_db[uid][field] = raw_text.title()
    except ValueError:
        await msg.answer("❌ Ошибка формата")
        return

    persist_user_data()
    try:
        await msg.delete()
        if ctx_data.get("prompt_id"):
            await msg.bot.delete_message(msg.chat.id, ctx_data["prompt_id"])
    except: pass
    
    await refresh_profile_ui(msg, uid)
    await state.clear()

@dp.callback_query(F.data == "done")
async def profile_finalize(cb: CallbackQuery):
    await cb.message.edit_text("✅ Готово! Главное меню:", reply_markup=main_menu())

# --- WORKOUTS ---
@dp.callback_query(F.data == "menu_workout")
async def fitness_hub(cb: CallbackQuery):
    await cb.message.edit_text("💪 <b>Тренировки</b>\nВыбери действие:", reply_markup=workout_menu(), parse_mode="HTML")

@dp.callback_query(F.data == "workout_start")
async def fitness_query_init(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("🔍 Введи активность (на англ, например <i>Running</i>):", parse_mode="HTML")
    await state.set_state(WorkoutForm.search_query)

@dp.message(StateFilter(WorkoutForm.search_query))
async def fitness_query_handler(msg: Message, state: FSMContext):
    q = msg.text.lower().strip()
    if exercise_data.empty:
        await msg.answer("⚠️ База упражнений пуста")
        await state.clear()
        return
    
    found = exercise_data[exercise_data['search_index'].str.contains(q, na=False)]
    if found.empty:
        await msg.answer("❌ Не найдено")
        return

    candidates = []
    for idx, row in found.head(6).iterrows():
        candidates.append((idx, row['Activity, Exercise or Sport (1 hour)']))
    
    if len(candidates) == 1:
        await trigger_duration_input(msg, state, candidates[0][0])
    else:
        await msg.answer("👇 Уточни:", reply_markup=workout_select_kb(candidates))
        await state.set_state(WorkoutForm.select_type)

@dp.callback_query(StateFilter(WorkoutForm.select_type), F.data.startswith("sel_work_"))
async def fitness_selection_handler(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.replace("sel_work_", ""))
    await trigger_duration_input(cb.message, state, idx)

async def trigger_duration_input(message_obj: Message, state: FSMContext, row_idx: int):
    record = exercise_data.loc[row_idx]
    name = str(record['Activity, Exercise or Sport (1 hour)'])
    factor = float(record['Calories per kg']) # Это за час
    
    await state.update_data(w_name=name, factor=factor)
    chat_id = message_obj.chat.id if isinstance(message_obj, Message) else message_obj.message.chat.id
    
    await bot.send_message(chat_id, f"Выбрано: <b>{name}</b>\n⏱ Время в минутах:", parse_mode="HTML")
    await state.set_state(WorkoutForm.duration)

@dp.message(StateFilter(WorkoutForm.duration))
async def fitness_log_session(msg: Message, state: FSMContext):
    try:
        mins = int(msg.text)
        if mins <= 0: raise ValueError
    except:
        await msg.answer("❌ Введи число > 0")
        return
    
    data = await state.get_data()
    uid = str(msg.from_user.id)
    weight = user_db.get(uid, {}).get('weight', 70)
    
    total_kcal = data['factor'] * weight * (mins / 60)
    
    entry = {
        "type": data['w_name'],
        "duration": mins,
        "kcal": round(total_kcal, 1),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
    
    user_db[uid].setdefault("workouts", []).append(entry)
    persist_user_data()
    
    await msg.answer(f"🔥 Сожжено: {total_kcal:.0f} ккал", reply_markup=main_menu())
    await state.clear()

# --- WATER ---
@dp.callback_query(F.data == "menu_water")
async def hydration_hub(cb: CallbackQuery):
    await cb.message.edit_text("💧 <b>Водный баланс:</b>", reply_markup=water_menu_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "water_add_250")
async def hydration_quick_add(cb: CallbackQuery):
    save_water(cb.from_user.id, 250)
    await cb.answer("Добавлено 250 мл!")
    await cb.message.edit_text("✅ Добавлено 250 мл.", reply_markup=water_menu_kb())

@dp.callback_query(F.data == "water_add")
async def hydration_add_prompt(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("💧 Введи мл:")
    await state.set_state(WaterForm.water_amount)

@dp.message(StateFilter(WaterForm.water_amount))
async def hydration_confirm_entry(msg: Message, state: FSMContext):
    try:
        vol = int(msg.text)
    except:
        await msg.answer("❌ Число.")
        return
    
    save_water(msg.from_user.id, vol)
    await msg.answer(f"✅ Добавлено {vol} мл", reply_markup=main_menu())
    await state.clear()

def save_water(user_id, amount):
    uid = str(user_id)
    user_db.setdefault(uid, {}).setdefault("water_log", []).append({
        "amount": amount,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    persist_user_data()

# --- FOOD & SCANNER FIX ---
@dp.callback_query(F.data == "menu_food")
async def nutrition_hub(cb: CallbackQuery):
    await cb.message.edit_text("🍽 <b>Трекер питания:</b>", reply_markup=food_menu(), parse_mode="HTML")

@dp.callback_query(F.data == "food_by_name")
async def nutrition_text_search(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("🍎 Название продукта:")
    await state.set_state(FoodForm.food_name)

@dp.message(StateFilter(FoodForm.food_name))
async def nutrition_search_handler(msg: Message, state: FSMContext):
    api = FoodAPI()
    res = api.search_food(msg.text)
    items = res.get("foods", {}).get("food", [])
    
    if not items:
        await msg.answer("❌ Не найдено.")
        await state.clear()
        return
        
    product = items[0]
    await state.update_data(fname=product['name'], kcal=product.get('calories', 0))
    await msg.answer(f"🔎 {product['name']}\n⚖ Вес (г):")
    await state.set_state(FoodForm.food_weight)

@dp.callback_query(F.data == "food_by_barcode")
async def nutrition_barcode_manual(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("🔢 Введи цифры штрихкода:")
    await state.set_state(FoodForm.food_barcode)

@dp.message(StateFilter(FoodForm.food_barcode))
async def nutrition_barcode_process(msg: Message, state: FSMContext):
    await process_barcode_logic(msg, msg.text.strip(), state)

@dp.callback_query(F.data == "food_by_photo")
async def nutrition_photo_prompt(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("📷 Пришли четкое фото штрихкода:")
    await state.set_state(FoodForm.food_photo)

@dp.message(StateFilter(FoodForm.food_photo), F.content_type == ContentType.PHOTO)
async def nutrition_photo_process(msg: Message, state: FSMContext):
    # === ИСПРАВЛЕННАЯ ЛОГИКА С PY_ZBAR ===
    photo_file = msg.photo[-1]
    file_info = await bot.get_file(photo_file.file_id)
    temp_path = f"temp_{photo_file.file_id}.jpg"
    
    await bot.download_file(file_info.file_path, destination=temp_path)
    
    code = None
    try:
        # Открываем через Pillow
        img = Image.open(temp_path)
        decoded_objects = decode_barcode(img)
        
        if decoded_objects:
            code = decoded_objects[0].data.decode("utf-8")
            logging.info(f"Barcode found: {code}")
        else:
            logging.warning("No barcode found in image")

    except Exception as e:
        logging.error(f"Decoding error: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    if not code:
        await msg.answer("❌ Штрихкод не распознан. Попробуй сфотографировать ближе или введи вручную.")
        return

    # Передаем найденный код в общую функцию
    await process_barcode_logic(msg, code, state)

async def process_barcode_logic(msg, code, state):
    api = FoodAPI()
    data = api.get_by_barcode(code)
    p_name = data.get("food", {}).get("name", "Unknown")
    
    if p_name == "Unknown":
        await msg.answer(f"❌ Продукт с кодом {code} не найден.")
        await state.clear()
        return
        
    f_data = data["food"]
    await state.update_data(fname=p_name, kcal=f_data.get('calories', 0))
    await msg.answer(f"📦 <b>{p_name}</b>\n⚖ Вес (г):", parse_mode="HTML")
    await state.set_state(FoodForm.food_weight)

@dp.message(StateFilter(FoodForm.food_weight))
async def nutrition_log_entry(msg: Message, state: FSMContext):
    try:
        w = float(msg.text)
    except:
        await msg.answer("❌ Число.")
        return
        
    d = await state.get_data()
    # kcal per 100g -> total
    total = (d['kcal'] * w) / 100
    
    uid = str(msg.from_user.id)
    user_db.setdefault(uid, {}).setdefault("food_log", []).append({
        "name": d['fname'],
        "kcal": total,
        "date": datetime.now().strftime("%Y-%m-%d")
    })
    persist_user_data()
    
    await msg.answer(f"✅ +{total:.0f} ккал", reply_markup=main_menu())
    await state.clear()

@dp.callback_query(F.data == "menu_goal")
async def progress_dashboard_view(cb: CallbackQuery):
    uid = str(cb.from_user.id)
    m = await derive_daily_metrics(uid)
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Еда
    food_logs = user_db.get(uid, {}).get("food_log", [])
    eaten = sum(x['kcal'] for x in food_logs if x['date'] == today)
    
    txt = (
        f"🎯 <b>Цели на сегодня:</b>\n"
        f"🔥 <b>Калории:</b> {eaten:.0f} / {m['cal_target']} (Сожжено: {m['cal_burned']:.0f})\n"
        f"💧 <b>Вода:</b> {m['water_current']} / {m['water_target']} мл\n"
    )
    rem = user_db[uid].get("reminder", {})
    await cb.message.edit_text(txt, reply_markup=goal_menu(uid, rem), parse_mode="HTML")

@dp.callback_query(F.data == "menu_visualization")
async def generate_stats_chart(cb: CallbackQuery):
    uid = str(cb.from_user.id)
    user_data = user_db.get(uid, {})
    
    # Готовим даты (последние 7 дней)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=6)
    date_range = pd.date_range(start_date, end_date).strftime("%Y-%m-%d").tolist()
    
    # Инициализируем словари нулями
    data_act = {d: 0 for d in date_range}
    data_food = {d: 0 for d in date_range}
    data_water = {d: 0 for d in date_range}
    
    for w in user_data.get("workouts", []):
        d_key = w["date"].split(" ")[0]
        if d_key in data_act:
            data_act[d_key] += w["kcal"]
            
    for f in user_data.get("food_log", []):
        d_key = f["date"]
        if d_key in data_food:
            data_food[d_key] += f["kcal"]

    for wat in user_data.get("water_log", []):
        d_key = wat["timestamp"].split(" ")[0]
        if d_key in data_water:
            data_water[d_key] += wat["amount"]
            

    df = pd.DataFrame({
        "Date": date_range,
        "Activity": [data_act[d] for d in date_range],
        "Food": [data_food[d] for d in date_range],
        "Water": [data_water[d] for d in date_range]
    })
    
    fig, axs = plt.subplots(3, 1, figsize=(8, 10), sharex=True)
    
    axs[0].bar(df["Date"], df["Activity"], color='#FFC872')
    axs[0].set_ylabel("Ккал сожжено")
    axs[0].set_title("Активность")
    axs[0].grid(axis='y', alpha=0.3)
    
    axs[1].bar(df["Date"], df["Food"], color='#701D1C')
    axs[1].set_ylabel("Ккал съедено")
    axs[1].set_title("Питание")
    axs[1].grid(axis='y', alpha=0.3)
    
    axs[2].bar(df["Date"], df["Water"], color='#5D83A6')
    axs[2].set_ylabel("Мл выпито")
    axs[2].set_title("Вода")
    axs[2].grid(axis='y', alpha=0.3)
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    
    await cb.message.answer_photo(
        photo=BufferedInputFile(buf.read(), filename="stats.png"),
        caption="📊 <b>Твоя статистика за 7 дней</b>",
        parse_mode="HTML"
    )
@dp.callback_query(F.data == "menu_profile")
async def profile_main_hub(cb: CallbackQuery):
    uid = str(cb.from_user.id)
    u_data = user_db.get(uid, {})
    
    # Словари для красивого вывода
    goal_map = {"lose": "📉 Сброс веса", "gain": "📈 Набор массы", "keep": "⚖️ Поддержание"}
    current_goal = goal_map.get(u_data.get("goal"), "Не установлена")
    
    text = (
        f"👤 <b>Твой личный профиль</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎯 Цель: <b>{current_goal}</b>\n"
        f"⚖️ Вес: <b>{u_data.get('weight', '—')} кг</b>\n"
        f"📏 Рост: <b>{u_data.get('height', '—')} см</b>\n"
        f"🎂 Возраст: <b>{u_data.get('age', '—')}</b>\n"
        f"🌍 Город: <b>{u_data.get('city', '—')}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Выбери действие:"
    )
    
    try:
        await cb.message.edit_text(text, reply_markup=profile_settings_kb(), parse_mode="HTML")
    except Exception as e:
        if "message is not modified" in str(e):
            await cb.answer()
        else:
            logging.error(f"Ошибка профиля: {e}")

@dp.callback_query(F.data == "setup_goal")
async def goal_selection_menu(cb: CallbackQuery):
    await cb.message.edit_text("🎯 <b>Выбери свою цель:</b>\n\n"
                               "📉 Сброс: ккал * 0.85\n"
                               "📈 Набор: ккал * 1.15", 
                               reply_markup=goal_selection_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("set_goal_"))
async def set_user_goal(cb: CallbackQuery):
    goal = cb.data.replace("set_goal_", "")
    uid = str(cb.from_user.id)
    
    if uid not in user_db:
        user_db[uid] = {
            "weight": 70, "height": 170, "age": 25, 
            "gender": "Male", "city": "Moscow", 
            "workouts": [], "water_log": [], "food_log": []
        }
    
    user_db[uid]["goal"] = goal
    persist_user_data()
    
    await cb.answer("🎯 Цель обновлена!")
    # Возвращаемся в меню профиля, чтобы увидеть обновленные данные
    await profile_main_hub(cb)

@dp.callback_query(F.data == "get_advice")
async def get_fitness_advice(cb: CallbackQuery):
    uid = str(cb.from_user.id)
    m = await derive_daily_metrics(uid)

    water_advice = [
        "💧 Ты пьешь мало воды. Попробуе добавить в стакан воды лимон, или приготовить отвар из регана",
        "🚰 Попробуй купить красивую бутылку воды и всегда носить её с собой. Так будет проще соблюдать водный баланс."
    ]
    activity_advice = [
        "🏃 Сегодня ты мало двигаешься. Пройдись 15 минут быстрым шагом, это ускоряет метаболизм и улучшает настроение!",
        "💪 Попробуй короткую тренировку дома: 10 приседаний + 10 отжиманий. Легко и эффективно!",
        "🤸 Добавь 5-минутную разминку перед работой. Достаточно простых наклонов и небольшой растяжки, чтобы почувствовать себя лучше."
    ]
    diet_advice = [
        "🥗 Замени часть гарнира на овощи: брокколи, шпинат, цветная капуста. Не забывай, что клетчкатка не менее важна, чем белок!",
        "🍎 Перекус яблоком или грушей вместо шоколадки может заметно сократить потребление калорий, но если сильно хочется, можно сьесть даже сникерс.🤫 Это поможет не сорваться. Главное, соблюдать норму калорий.",
        "🥒 Современные ученые считают, что голод значительно притупляется, когда человек сьедает дневную норму белка. Попробуй, может, именно его не хватает твоему организму."
    ]
    goal_advice = {
        "lose": ["⚖️ Цель сбросить вес? Замени майонез греческим йогуртом с солью и чесноком, так ты снизишь потребление жиров и тебе будет проще добрать белок."],
        "gain": ["📈 Добавь к ужину порцию сложных углеводов: овсянка, гречка или картофель. Это база для набора массы."],
        "keep": ['🌟 Ты идешь по плану! Старайся соблюдать режим сна и поддерживать активность, чтобы твое тело сказало тебе "спасибо"']}

    # Логика выбора совета
    if m['water_current'] < m['water_target'] * 0.5:
        advice = random.choice(water_advice)
    elif m['cal_burned'] < 100:
        advice = random.choice(activity_advice)
    elif m['goal'] in ["lose", "gain"]:
        advice = random.choice(diet_advice + goal_advice[m['goal']])
    else:
        advice = random.choice(goal_advice["keep"])

    await cb.message.answer(f"💡 <b>Совет для тебя:</b>\n\n{advice}", parse_mode="HTML")
    await cb.answer()

async def main():
    logging.info("🤖 Bot starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        threading.Thread(target=run_web, daemon=True).start()
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
