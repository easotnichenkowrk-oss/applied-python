from aiogram.fsm.state import StatesGroup, State

class ProfileForm(StatesGroup):
    weight = State()
    height = State()
    age = State()
    gender = State()  # Заменили activity на gender
    city = State()

class FoodForm(StatesGroup):
    food_name = State()
    food_barcode = State()
    food_photo = State()
    food_weight = State()

class WaterForm(StatesGroup):
    water_amount = State()

class WorkoutForm(StatesGroup):
    search_query = State()    # Ввод названия
    select_type = State()     # Выбор из списка, если найдено несколько
    duration = State()        # Ввод времени