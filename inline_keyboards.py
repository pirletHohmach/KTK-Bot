import json
import database
import requests
import random
import asyncio
import hashlib


from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.types.web_app_info import WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import Router

from datetime import datetime, timedelta


with open('config.json', 'r', encoding="utf-8") as config_file:
    config = json.load(config_file)


COLLEGE_GROUPS = sorted(config["COLLEGE_GROUPS"])
BUTTONS_PER_PAGE = 8

TEACHERS = sorted(config["TEACHERS"])
TEACHERS_PER_PAGE = 8

SCHEDULE_API_URL = config["SCHEDULE_API_URL"]
MOODLE_URL = config["MOODLE_URL"]
username_jokes = config["USERNAME_JOKES"]
router = Router()



class GroupChoice(StatesGroup):
    waiting_group = State()

#Создание клавиатуры для выбора группы
async def create_group_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    start_index = page * BUTTONS_PER_PAGE
    end_index = start_index + BUTTONS_PER_PAGE

    button_text = f"Нет доступных групп, все умерли от нейротоксина :)"

    total_pages = (len(COLLEGE_GROUPS) + BUTTONS_PER_PAGE - 1) // BUTTONS_PER_PAGE

    buttons = []

    current_groups = COLLEGE_GROUPS[start_index:end_index]

    if not current_groups:
        return InlineKeyboardMarkup(
            InlineKeyboardButton=[[InlineKeyboardButton(text=button_text, callback_data="none")]])

    for i in range(0, len(current_groups), 2):
        row = []
        # Первая кнопка в строке
        (row.append
            (InlineKeyboardButton(
            text=current_groups[i],
            callback_data=f"group_{current_groups[i]}")))

        if i + 1 < len(current_groups):
            row.append(
                InlineKeyboardButton(
                    text=current_groups[i + 1],
                    callback_data=f"group_{current_groups[i + 1]}"))
        buttons.append(row)

    nav_buttons = []

    # Условие для первой страницы
    if page == 0:
        if total_pages > 1:
            nav_buttons.append(InlineKeyboardButton(
                text="Далее➡️",
                callback_data=f"page-{page + 1}"))

    # Условие для последней страницы
    elif page == total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️Назад",
            callback_data=f"page-{page - 1}"))

    # Условие для промежуточных страниц
    else:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️Назад",
            callback_data=f"page-{page - 1}"))

        nav_buttons.append(InlineKeyboardButton(
            text="Далее➡️",
            callback_data=f"page-{page + 1}"))

    # Если есть навигационные кнопки, добавляем их
    if nav_buttons:
        buttons.append(nav_buttons)

    # Добавляем кнопку "На главную"
    buttons.append([InlineKeyboardButton(text="На главную", callback_data="home")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(lambda c: c.data == "change-group")
async def change_group_callback(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        f"{random.choice(username_jokes)} выбери свою группу с такими же как и ты или напиши:\n",
        reply_markup=await create_group_keyboard()
    )
    await state.set_state(GroupChoice.waiting_group)
    await state.update_data(message_id=callback_query.message.message_id)
    await callback_query.answer()


@router.callback_query(lambda c: c.data.startswith('page-'))
async def handle_page_change(callback_query: CallbackQuery):
    page = int(callback_query.data.split('-')[1])

    # Обновляем сообщение с новой клавиатурой для выбора группы
    await callback_query.message.edit_text(
        f"{random.choice(username_jokes)} выбери свою группу с такими же как и ты:\n",
        reply_markup=await create_group_keyboard(page=page)
    )
    await callback_query.answer()


#Обработчик запросов callback_data для клавиатуры с группами
@router.callback_query(lambda c: c.data.startswith('group_'))
async def select_group(callback_query: CallbackQuery, state: FSMContext):
    group = callback_query.data.split('_')[1]
    user_id = callback_query.from_user.id

    # Обновляем группу пользователя
    database.update_user_group(user_id, group)

    # Изменение сообщения обратно на начальное состояние
    await callback_query.message.edit_text(
        f"Группа \"{group}\" успешно установлена.\n\nСписок команд:",
        reply_markup=await create_help_keyboard()
    )
    await state.clear()
    await callback_query.answer()


@router.message(GroupChoice.waiting_group)
async def process_text_group(message: Message, state: FSMContext):
    user_id = message.from_user.id
    group = message.text.strip()  # Удаляем лишние пробелы

    data = await state.get_data()
    if message_id := data.get('message_id'):
        try:
            await message.bot.delete_message(message.chat.id, message_id)
        except Exception as e:
            print(f"Ошибка при удалении сообщения: {e}")

    # Проверяем, является ли группа валидной
    if group not in COLLEGE_GROUPS:
        await message.answer(
            "Пожалуйста, введите корректное название группы из списка или напиши\n\n",
            reply_markup=await create_group_keyboard()
        )
        return  # Завершаем функцию, чтобы дать пользователю еще один шанс

    # Если группа валидна, обновляем группу пользователя
    database.update_user_group(user_id, group)

    await message.answer(f"Группа \"{group}\" успешно установлена.")
    await state.clear()


# Функция создания клавиатуры команд
async def create_help_keyboard() -> InlineKeyboardMarkup:
    command_buttons = [
        [InlineKeyboardButton(text="Поменять группу👥", callback_data="change-group")],
        [
            InlineKeyboardButton(text="📚Расписание на сегодня", callback_data="schedule-today"),
            InlineKeyboardButton(text="Расписание на завтра📚", callback_data="schedule-tomorrow")
        ],
        [InlineKeyboardButton(text="Преподаватели👨‍🏫", callback_data="teachers")],
        [InlineKeyboardButton(text="Открыть Moodle", web_app=WebAppInfo(url=MOODLE_URL) )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=command_buttons)


def get_share_keyboard(schedule_text: str):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Поделиться",
            switch_inline_query=schedule_text
        )
    ]])


@router.callback_query(lambda c: c.data in ["schedule-today", "schedule-tomorrow", "change-group"])
async def handle_schedule_and_group(callback_query: CallbackQuery, state: FSMContext):
    data = callback_query.data
    user_id = callback_query.from_user.id

    if data in ["schedule-today", "schedule-tomorrow"]:
        group_name = database.get_user_group(user_id)
        today = datetime.now()
        date_to_check = today if data == "schedule-today" else today + timedelta(days=1)
        date_str = date_to_check.strftime('%Y-%m-%d')

        # Проверка на выходные
        if today.weekday() == 6 and data == "schedule-today":  # Воскресенье, запрос на сегодня
            await callback_query.message.edit_text(
                "Сегодня выходной",
                reply_markup=get_share_keyboard("Сегодня выходной")
            )
            await callback_query.answer()
            return
        elif today.weekday() == 7 and data == "schedule-tomorrow":  # Воскресенье, запрос на завтра
            await callback_query.message.edit_text(
                "Завтра выходной",
                reply_markup=get_share_keyboard("Завтра выходной")
            )
            await callback_query.answer()
            return

        if not group_name:
            await callback_query.message.answer("Сначала установи группу")
            await callback_query.answer()
            return

        await callback_query.message.edit_text("Отправляем запрос...")
        response = requests.get(f"{SCHEDULE_API_URL}?date={date_str}&type=None")
        data_response = response.json()

        if data_response.get("result"):
            schedule_list = data_response.get("obj", {}).get("schedule_list_data", [])
            start_times = data_response.get("obj", {}).get("start_at", [])
            end_times = data_response.get("obj", {}).get("end_at", [])

            filtered_schedule = [item for item in schedule_list if item.get("collective") == group_name]

            if filtered_schedule:
                schedule_message = []
                current_number = 1  # Нумерация для пар

                for i, item in enumerate(filtered_schedule):
                    start_time_str = start_times[item['class_index'] - 1]
                    end_time_str = end_times[item['class_index'] - 1]

                    start_time = datetime.strptime(start_time_str, '%H:%M:%S').strftime('%H:%M')
                    end_time = datetime.strptime(end_time_str, '%H:%M:%S').strftime('%H:%M')

                    subject = item.get('subject', 'Без названия').replace("/", "").replace("moodle/", "moodle").strip()

                    if i > 0:
                        prev_end_time_str = end_times[filtered_schedule[i - 1]['class_index'] - 1]
                        prev_end_time = datetime.strptime(prev_end_time_str, '%H:%M:%S')
                        current_start_time = datetime.strptime(start_time_str, '%H:%M:%S')

                        if current_start_time > prev_end_time:
                            current_number += 1

                    schedule_message.append(
                        f"{current_number}. [{start_time} - {end_time}] • "
                        f"{subject} • "
                        f"{item.get('teacher', 'Не указан')} • "
                        f"Аудитория: {item.get('classroom', 'Не указана')}"
                    )

                final_message = (
                        f"Расписание на {'сегодня' if data == 'schedule-today' else 'завтра'} "
                        f"для группы {group_name}:\n\n" + "\n\n".join(schedule_message)
                )

                await callback_query.message.edit_text(
                    final_message,
                    reply_markup=get_share_keyboard(final_message)
                )
            else:
                no_schedule_message = (
                    f"На {'сегодня' if data == 'schedule-today' else 'завтра'} "
                    f"нет расписания для группы {group_name}"
                )
                await callback_query.message.edit_text(
                    no_schedule_message,
                    reply_markup=get_share_keyboard(no_schedule_message)
                )
        else:
            error_message = (
                f"Не удалось получить расписание на "
                f"{'сегодня' if data == 'schedule-today' else 'завтра'}"
            )
            await callback_query.message.edit_text(
                error_message,
                reply_markup=get_share_keyboard(error_message)
            )
        await callback_query.answer()

    elif data == "change-group":
        await callback_query.message.edit_text(
            f"{random.choice(username_jokes)} выбери свою группу с такими же как и ты:\n",
            reply_markup=await create_group_keyboard()
        )
        await state.set_state(GroupChoice.waiting_group)
        await state.update_data(message_id=callback_query.message.message_id)
        await callback_query.answer()


async def create_teachers_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    start_index = page * TEACHERS_PER_PAGE
    end_index = start_index + TEACHERS_PER_PAGE
    total_pages = (len(TEACHERS) + TEACHERS_PER_PAGE - 1) // TEACHERS_PER_PAGE

    buttons = []
    current_teachers = TEACHERS[start_index:end_index]

    # Создаем кнопки для преподавателей (2 в ряд)
    for i in range(0, len(current_teachers), 2):
        row = []
        # Добавляем первого преподавателя без рейтинга
        row.append(InlineKeyboardButton(
            text=f"{current_teachers[i]}",
            callback_data=f"teacher_{current_teachers[i]}"
        ))

        # Если есть второй преподаватель в ряду
        if i + 1 < len(current_teachers):
            row.append(InlineKeyboardButton(
                text=f"{current_teachers[i + 1]}",
                callback_data=f"teacher_{current_teachers[i + 1]}"
            ))
        buttons.append(row)

    # Добавляем кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️Назад", callback_data=f"teachers_page-{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Далее➡️", callback_data=f"teachers_page-{page + 1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    # Добавляем кнопку "На главную"
    buttons.append([InlineKeyboardButton(text="На главную", callback_data="home")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.callback_query(lambda c: c.data == "home")
async def handle_home_button(callback_query: CallbackQuery, state: FSMContext):
    # Очищаем состояние, если оно есть
    await state.clear()
    # Возвращаемся на главную страницу с основным меню
    await callback_query.message.edit_text(
        "Список команд:",
        reply_markup=await create_help_keyboard()
    )
    await callback_query.answer()

async def create_teacher_actions_keyboard(teacher_name: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🚪Узнать кабинеты сегодня", callback_data=f"classrooms_today_{teacher_name}"),
            InlineKeyboardButton(text="Узнать кабинеты завтра🚪", callback_data=f"classrooms_tomorrow_{teacher_name}")
        ],
        [
            InlineKeyboardButton(text="Поставить рейтинг⭐", callback_data=f"rate_{teacher_name}")
        ],
        [
            InlineKeyboardButton(text="Назад к преподавателям", callback_data="back_to_teachers")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)



async def create_rating_keyboard(teacher_name: str) -> InlineKeyboardMarkup:
    buttons = []
    # Создаем ряд кнопок с оценками от 1 до 5
    rating_buttons = [InlineKeyboardButton(
        text=str(i),
        callback_data=f"setrate_{teacher_name}_{i}"
    ) for i in range(1, 6)]
    buttons.append(rating_buttons)
    # Добавляем кнопку "Назад"
    buttons.append([InlineKeyboardButton(text="Назад", callback_data=f"teacher_{teacher_name}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(lambda c: c.data == "teachers")
async def show_teachers(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "Выберите преподавателя:",
        reply_markup=await create_teachers_keyboard()
    )
    await callback_query.answer()


@router.callback_query(lambda c: c.data.startswith("teachers_page-"))
async def handle_teachers_page(callback_query: CallbackQuery):
    page = int(callback_query.data.split('-')[1])
    await callback_query.message.edit_text(
        "Выберите преподавателя:",
        reply_markup=await create_teachers_keyboard(page)
    )
    await callback_query.answer()


@router.callback_query(lambda c: c.data.startswith("teacher_"))
async def handle_teacher_selection(callback_query: CallbackQuery):
    teacher_name = callback_query.data.split('_', 1)[1]
    rating_info = database.get_teacher_rating(teacher_name)

    # Проверка на целое значение для отображения без десятичной части
    if rating_info:
        average_rating = rating_info['average_rating']
        if average_rating == int(average_rating):  # Проверка, является ли рейтинг целым числом
            rating_text = f"\nТекущий рейтинг: {int(average_rating)}/5"
        else:
            rating_text = f"\nТекущий рейтинг: {average_rating:.1f}/5"  # Формат с одной десятичной
    else:
        rating_text = ""

    await callback_query.message.edit_text(
        f"Преподаватель: {teacher_name}{rating_text}\nВыберите действие:",
        reply_markup=await create_teacher_actions_keyboard(teacher_name)
    )
    await callback_query.answer()


@router.callback_query(lambda c: c.data.startswith("classrooms_today_"))
async def show_teacher_classrooms_today(callback_query: CallbackQuery):
    teacher_name = callback_query.data.split('_', 2)[2]

    # Получаем расписание на сегодня
    today = datetime.now().strftime('%Y-%m-%d')
    response = requests.get(f"{SCHEDULE_API_URL}?date={today}&type=None")
    data = response.json()

    classroom_times = []
    if data.get("result"):
        schedule_list = data.get("obj", {}).get("schedule_list_data", [])
        start_times = data.get("obj", {}).get("start_at", [])
        end_times = data.get("obj", {}).get("end_at", [])

        for item in schedule_list:
            if item.get("teacher") == teacher_name:
                classroom = item.get("classroom", "Не указана")
                start_time = datetime.strptime(start_times[item['class_index'] - 1], '%H:%M:%S').strftime('%H:%M')
                end_time = datetime.strptime(end_times[item['class_index'] - 1], '%H:%M:%S').strftime('%H:%M')
                classroom_times.append({
                    'classroom': classroom,
                    'time': f"<b>{start_time} - {end_time}</b>"
                })

    # Сортируем по времени начала занятия (убираем HTML-теги для сортировки)
    classroom_times.sort(key=lambda x: x['time'].replace('<b>', '').replace('</b>', ''))

    # Формируем текст с нумерацией
    classrooms_text = "\n".join(
        f"{i}. {item['classroom']} | {item['time']}"
        for i, item in enumerate(classroom_times, 1)
    ) if classroom_times else "Сегодня нет занятий"

    await callback_query.message.edit_text(
        f"Кабинеты преподавателя {teacher_name} на сегодня:\n\n{classrooms_text}",
        reply_markup=await create_teacher_actions_keyboard(teacher_name),
        parse_mode='HTML'
    )
    await callback_query.answer()


@router.callback_query(lambda c: c.data.startswith("classrooms_tomorrow_"))
async def show_teacher_classrooms_tomorrow(callback_query: CallbackQuery):
    teacher_name = callback_query.data.split('_', 2)[2]

    # Получаем расписание на завтра
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    response = requests.get(f"{SCHEDULE_API_URL}?date={tomorrow}&type=None")
    data = response.json()

    classroom_times = []
    if data.get("result"):
        schedule_list = data.get("obj", {}).get("schedule_list_data", [])
        start_times = data.get("obj", {}).get("start_at", [])
        end_times = data.get("obj", {}).get("end_at", [])

        for item in schedule_list:
            if item.get("teacher") == teacher_name:
                classroom = item.get("classroom", "Не указана")
                start_time = datetime.strptime(start_times[item['class_index'] - 1], '%H:%M:%S').strftime('%H:%M')
                end_time = datetime.strptime(end_times[item['class_index'] - 1], '%H:%M:%S').strftime('%H:%M')
                classroom_times.append({
                    'classroom': classroom,
                    'time': f"<b>{start_time} - {end_time}</b>"
                })

    # Сортируем по времени начала занятия (убираем HTML-теги для сортировки)
    classroom_times.sort(key=lambda x: x['time'].replace('<b>', '').replace('</b>', ''))

    # Формируем текст с нумерацией
    classrooms_text = "\n".join(
        f"{i}. {item['classroom']} | {item['time']}"
        for i, item in enumerate(classroom_times, 1)
    ) if classroom_times else "Завтра нет занятий"

    await callback_query.message.edit_text(
        f"Кабинеты преподавателя {teacher_name} на завтра:\n\n{classrooms_text}",
        reply_markup=await create_teacher_actions_keyboard(teacher_name),
        parse_mode='HTML'
    )
    await callback_query.answer()


@router.callback_query(lambda c: c.data.startswith("rate_"))
async def show_rating_options(callback_query: CallbackQuery):
    teacher_name = callback_query.data.split('_', 1)[1]
    await callback_query.message.edit_text(
        f"Выберите оценку для преподавателя {teacher_name}:",
        reply_markup=await create_rating_keyboard(teacher_name)
    )
    await callback_query.answer()


@router.callback_query(lambda c: c.data.startswith("setrate_"))
async def set_teacher_rating(callback_query: CallbackQuery):
    _, teacher_name, rating = callback_query.data.split('_')
    success, msg = database.rate_teacher(callback_query.from_user.id, teacher_name, int(rating))

    if success:
        rating_info = database.get_teacher_rating(teacher_name)
        # Форматируем рейтинг в зависимости от его типа
        average_rating = rating_info['average_rating']
        if average_rating == int(average_rating):
            rating_text = f"{int(average_rating)}/5"
        else:
            rating_text = f"{average_rating:.1f}/5"

        await callback_query.message.edit_text(
            f"Оценка для {teacher_name} принята\n"
            f"Текущий рейтинг: {rating_text}\n"
            f"Всего оценок: {rating_info['total_ratings']}",
            reply_markup=await create_teacher_actions_keyboard(teacher_name)
        )
    else:
        await callback_query.answer(f"Ошибка: {msg}")


@router.callback_query(lambda c: c.data == "back_to_teachers")
async def back_to_teachers_list(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "Выберите преподавателя:",
        reply_markup=await create_teachers_keyboard()
    )
    await callback_query.answer()


async def check_schedule_and_notify(bot):  # Добавляем параметр bot
    while True:
        try:
            now = datetime.now()
            tomorrow = (now + timedelta(days=1)).strftime('%Y-%m-%d')

            response = requests.get(f"{SCHEDULE_API_URL}?date={tomorrow}&type=None")
            if not response.ok:
                await asyncio.sleep(120)
                continue

            schedule_data = response.json()
            if not schedule_data.get("result"):
                await asyncio.sleep(120)
                continue

            schedule_hash = hashlib.md5(json.dumps(schedule_data, sort_keys=True).encode()).hexdigest()
            last_hash = database.get_last_schedule_hash(tomorrow)

            if last_hash != schedule_hash:
                database.update_schedule_check(tomorrow, schedule_hash)
                schedule_list = schedule_data.get("obj", {}).get("schedule_list_data", [])

                if schedule_list:
                    schedule_by_group = {}
                    for item in schedule_list:
                        group = item['collective']
                        if group not in schedule_by_group:
                            schedule_by_group[group] = []
                        schedule_by_group[group].append(
                            f"{item['subject']} | {item['teacher']} | Аудитория: {item['classroom']}"
                        )

                    user_ids = database.get_all_user_ids()
                    for user_id in user_ids:
                        user_group = database.get_user_group(user_id)
                        if user_group and user_group in schedule_by_group:
                            schedule_text = "\n".join(schedule_by_group[user_group])
                            message = f"Появилось расписание на завтра ({tomorrow}) для группы {user_group}:\n\n{schedule_text}"
                            try:
                                await bot.send_message(user_id, message)  # Теперь бот доступен
                            except Exception as e:
                                print(f"Failed to send message to user {user_id}: {e}")

            await asyncio.sleep(120)

        except Exception as e:
            print(f"Error in schedule checker: {e}")
            await asyncio.sleep(120)