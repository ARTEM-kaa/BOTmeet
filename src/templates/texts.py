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

async def comment_prompt(full_name: str) -> str:
    return f"Снизу вы можете оставить ОДИН комментарий пользователю {full_name}:"

async def rating_prompt(full_name: str) -> str:
    return f"Поставьте оценку пользователю {full_name}:"

async def updated_successfully() -> str:
    return "Комментарий отправлен ✅"

async def no_profiles_left() -> str:
    return "Анкеты закончились 😔"

async def choose_stars(full_name: str) -> str:
    return f"Выберите количество звёзд для {full_name}:"

async def error_comment() -> str:
    return "Вы уже отправляли комментарий этому пользователю"

async def comment_sent() -> str:
    return "Комментарий отправлен ✅"

async def error_rate() -> str:
    return "Ошибка сохранения оценки"

async def rate_sent() -> str:
    return "Оценка сохранена ✅"

async def error_dislike() -> str:
    return "Произошла ошибка при сохранении дизлайка"

async def error_like() -> str:
    return "Произошла ошибка при сохранении лайка"

async def error_photo() -> str:
    return "Фото слишком большое (максимум 10MB)"

async def error_photo_phormat() -> str:
    return "Пожалуйста, отправьте фото в формате JPG или PNG"

async def prohibited_characters() -> str:
    return "Описание содержит запрещенные символы"

async def bio_length_error() -> str:
    return "Описание должно быть не длиннее 500 символов"

async def data_bio_error() -> str:
    return "Пожалуйста, введите текст"

async def age_length_error() -> str:
    return "Возраст должен быть от 10 до 110 лет"

async def data_name_error_char() -> str:
    return "ФИО не должно содержать цифр"

async def data_name_error() -> str:
    return "ФИО должно содержать только буквы"
