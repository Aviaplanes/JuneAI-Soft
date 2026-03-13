from .email_input import (
    input_email_only,
    click_continue_button,
    click_checkbox,
    input_mail,  # deprecated, для совместимости
)
from .auto_login import human_click_if_exists
from .login_check import set_login_true, set_login_false

__all__ = [
    "input_email_only",
    "click_continue_button",
    "click_checkbox",
    "input_mail",
    "human_click_if_exists",
    "set_login_true",
    "set_login_false",
]
