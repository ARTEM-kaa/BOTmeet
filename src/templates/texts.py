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
