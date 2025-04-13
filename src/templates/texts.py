_ = lambda text: text

async def start_message():
    return _(
        "Привет, это бот для знакомств! 👋\n"
        "Давай заполним анкету чтобы начать знакомится. ⬇️"
    )

async def ask_full_name():
    return _("Введите ФИО в формате: Фамилия Имя Отчество. \nИменно в таком порядке через пробел.")

async def ask_full_name_again():
    return _("Пожалуйста, введите ФИО в формате: Фамилия Имя Отчество.")

async def ask_age():
    return _("Теперь введите свой возраст цифрой:")

async def ask_age_again():
    return _("Возраст должен быть числом. Попробуйте ещё раз.")

async def ask_rating_again():
    return _("Рейтинг должен быть числом. Попробуйте ещё раз.")

async def ask_gender():
    return _("Выберите свой пол:")

async def ask_bio():
    return _("Теперь расскажите о себе. Вы можете написать свои качества или историю.")

async def ask_photo():
    return _("И последний штрих — отправь мне своё фото, которое будет аватаркой.")

async def ask_photo_again():
    return _("Это не похоже на фото. Пожалуйста, пришли картинку.")

async def success():
    return _("Отлично! ✅\nТвоя анкета заполненна и теперь ты можешь начать знакомства.")

async def summary(data):
    return _(
        f"{data['full_name']}, {data['age']} лет\n"
        f"Пол: {data['gender']}\n"
        f"О себе: {data['bio']}"
    )

async def set_preferences():
    return _("Тут вы можете указать свои предпочтения по подбору анкет.\nВыберите какие предпочтения вы хотите установить:")

async def likes_count(count: int) -> str:
    if count == 0:
        return "😔 Пока никто не поставил тебе лайк."
    return f"❤️ Тебе поставили <b>{count}</b> лайк(ов)!"

async def rating_info(avg_rating: float, total: int) -> str:
    if total == 0:
        return "😶 Пока никто не поставил тебе оценку."
    return (
        f"📊 Твой рейтинг: <b>{round(avg_rating, 2)}</b> ⭐️\n"
        f"Количество оценок: <b>{total}</b>"
    )

async def edit_profile_text():
    return "Редактирование профиля!\nВыбери, что хочешь изменить:"

async def edit_photo():
    return _("Пришли мне новое фото, которое будет аватаркой!")

async def edit_full_name():
    return _("Введите своё новое ФИО в формате: Фамилия Имя Отчество.")

async def edit_age():
    return _("Введите свой новый возраст цифрой:")

async def edit_bio():
    return _("Можете придумать новый расссказ о себе:")

async def updated_successfully():
    return "✅ Профиль успешно обновлён!"

async def min_age():
    return "Введите минимальный возраст цифрой:"

async def max_age():
    return "Введите максимальный возраст цифрой:"

async def min_rating():
    return "Введите минимальный рейтинг:"

async def max_rating():
    return "Введите максимальный рейтинг:"

async def min_age_saved():
    return "✅ Минимальный возраст сохранён."

async def max_age_saved():
    return "✅ Максимальный возраст сохранён."

async def min_rating_saved():
    return "✅ Минимальный рейтинг сохранён."

async def max_rating_saved():
    return "✅ Максимальный рейтинг сохранён."