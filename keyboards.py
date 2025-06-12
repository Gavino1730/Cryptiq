"""
keyboards.py

Defines keyboard layouts and helper functions for Telegram inline and reply keyboards in Cryptiq bot.
Used to provide interactive menus and options to users.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# Example of an inline keyboard
async def start_keyboard():
    keyboard = InlineKeyboardMarkup()
    button1 = InlineKeyboardButton("Button 1", callback_data="button1")
    button2 = InlineKeyboardButton("Button 2", callback_data="button2")
    keyboard.add(button1, button2)
    return keyboard

# Example of a reply keyboard
async def main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = KeyboardButton("Menu 1")
    button2 = KeyboardButton("Menu 2")
    keyboard.add(button1, button2)
    return keyboard

# (Add or update docstrings and comments for each keyboard layout/helper as you move logic in)