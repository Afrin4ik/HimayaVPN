from aiogram.types import User


def render_main_menu(
        *,
        user: User,
) -> str:
    greeting: str = "👋 Привет!"

    if user.username:
        greeting = f"👋 Привет, @{user.username}!"
    else:
        greeting = f"👋 Привет, {user.full_name}"

    return (
        f"{greeting}\n\n"
        f"👨‍💻 Для продолжения работы выберите действие ниже"
    )
