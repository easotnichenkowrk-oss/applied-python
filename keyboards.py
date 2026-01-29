from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# =======================
# START KB
# =======================
def start_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Старт", callback_data="start_form")]
        ]
    )

# =======================
# PROFILE KB
# =======================
def profile_kb(filled: dict):
    # Гендер: отображаем иконку или текст
    gender_text = "—"
    if filled.get('gender') == 'Male':
        gender_text = "👨 Мужской"
    elif filled.get('gender') == 'Female':
        gender_text = "👩 Женский"

    buttons = [
        InlineKeyboardButton(
            text=f"⚖ Вес: {filled.get('weight', '—')}",
            callback_data="edit_weight"
        ),
        InlineKeyboardButton(
            text=f"📏 Рост: {filled.get('height', '—')}",
            callback_data="edit_height"
        ),
        InlineKeyboardButton(
            text=f"🎂 Возраст: {filled.get('age', '—')}",
            callback_data="edit_age"
        ),
        InlineKeyboardButton(
            text=f"⚧ Пол: {gender_text}",
            callback_data="edit_gender"
        ),
        InlineKeyboardButton(
            text=f"🌍 Город: {filled.get('city', '—')}",
            callback_data="edit_city"
        ),
    ]

    keyboard = [[b] for b in buttons]

    if all([
        filled.get("weight"),
        filled.get("height"),
        filled.get("age"),
        filled.get("gender"),
        filled.get("city"),
    ]):
        keyboard.append(
            [InlineKeyboardButton(text="✅ Готово", callback_data="done")]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Выбор пола
def gender_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👨 Мужской", callback_data="gender_Male")],
            [InlineKeyboardButton(text="👩 Женский", callback_data="gender_Female")]
        ]
    )

# =======================
# MAIN MENU
# =======================
def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧾 Анкета", callback_data="menu_profile")],
            [InlineKeyboardButton(text="🏋️ Тренировка", callback_data="menu_workout")],
            [InlineKeyboardButton(text="💧 Вода", callback_data="menu_water")],
            [InlineKeyboardButton(text="🍽 Еда", callback_data="menu_food")],
            [InlineKeyboardButton(text="🎯 Цель", callback_data="menu_goal")],
            [InlineKeyboardButton(text="📊 Визуализация", callback_data="menu_visualization")],
        ]
    )

# =======================
# WORKOUT KB
# =======================
def workout_menu():
    # Начальное меню тренировок теперь просто предлагает добавить новую
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить тренировку", callback_data="workout_start")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ]
    )

def workout_select_kb(options):
    """
    Генерирует кнопки для выбора тренировки из найденных вариантов.
    options: список словарей или кортежей (index, name)
    """
    buttons = []
    for idx, name in options:
        # Обрезаем слишком длинные названия для кнопки
        btn_text = name[:30] + "..." if len(name) > 30 else name
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"sel_work_{idx}")])
    
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# =======================
# WATER & FOOD & GOAL
# =======================
def water_menu_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💧 Добавить воды", callback_data="water_add")],
            [InlineKeyboardButton(text="📜 История", callback_data="water_history")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ]
    )

def food_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔎 По названию", callback_data="food_by_name")],
            [InlineKeyboardButton(text="📦 По штрих-коду", callback_data="food_by_barcode")],
            [InlineKeyboardButton(text="📷 По фото", callback_data="food_by_photo")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ]
    )

def goal_menu(user_id, reminder_data):
    reminder_enabled = reminder_data.get("enabled", False)
    reminder_time = reminder_data.get("time", "08:00")
    toggle_text = "✅ Вкл" if reminder_enabled else "❌ Выкл"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"⏰ Время: {reminder_time}", callback_data="goal_time"),
                InlineKeyboardButton(text=toggle_text, callback_data="goal_toggle")
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ]
    )