"""
keyboards.py

Defines keyboard layouts and helper functions for Telegram inline and reply keyboards in Cryptiq bot.
Used to provide interactive menus and options to users.
"""

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# Example of an inline keyboard
def start_keyboard():
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Button 1", callback_data="button1"),
         InlineKeyboardButton("Button 2", callback_data="button2")]
    ])
    return keyboard

# Example of a reply keyboard
def main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("Menu 1"), KeyboardButton("Menu 2")]
    ], resize_keyboard=True)
    return keyboard

# (Add or update docstrings and comments for each keyboard layout/helper as you move logic in)