"""
utils.py

Utility functions for Cryptiq bot, including market data fetching, error logging, prompt building, and chart helpers.
These functions are used by handlers and other modules to keep code DRY and maintainable.
"""
import os
import json
import datetime
import requests
import pytz
import logging
import matplotlib.pyplot as plt
import io
import asyncio

# Configure logging for the entire bot
LOG_FILE = os.path.join(os.path.dirname(__file__), "cryptiq.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cryptiq")

# --- Error logging helper ---
def log_error(e, context=""):
    """
    Logs errors to both error_log.json and the main log file with traceback and context.

    Args:
        e (Exception): The exception object.
        context (str): Additional context about the error.
    """
    logger.error(f"[ERROR] {context}: {e}", exc_info=True)
    try:
        with open("error_log.json", "a") as f:
            f.write(f"{datetime.datetime.now()}: {context}: {e}\n")
    except Exception as file_err:
        logger.error(f"Failed to write to error_log.json: {file_err}")

# --- Market data helper ---
COIN_SYMBOL_TO_ID = {
    'btc': 'bitcoin',
    'bitcoin': 'bitcoin',
    'ltc': 'litecoin',
    'litecoin': 'litecoin',
    # Add more mappings as needed
}
COINGECKO_SIMPLE_PRICE_API = "https://api.coingecko.com/api/v3/simple/price?vs_currencies=usd&include_24hr_change=true&ids={ids}"

def get_market_data_for_coins(coin_symbols, debug_message=None):
    """
    Fetch market data for a list of coin symbols from the CoinGecko API.

    Args:
        coin_symbols (list): A list of coin symbols (e.g., ['btc', 'ltc']).
        debug_message (function): Optional. A callback function for debug messages.

    Returns:
        dict: A dictionary with market data for the requested coins.
    """
    ids = [COIN_SYMBOL_TO_ID.get(str(s).lower(), str(s).lower()) for s in coin_symbols]
    ids = [i for i in ids if i is not None]
    ids_str = '%2C'.join(ids)
    url = COINGECKO_SIMPLE_PRICE_API.format(ids=ids_str)
    try:
        print(f"[CoinGecko] Requesting URL: {url}")
        resp = requests.get(url)
        print(f"[CoinGecko] Status: {resp.status_code}")
        data = resp.json()
        print("[CoinGecko] Response:", data)
        if not data or any('error' in v for v in data.values() if isinstance(v, dict)):
            print("[CoinGecko] API returned error or empty data.")
            if debug_message is not None:
                debug_message(f"CoinGecko API error or empty data. URL: {url} Response: {data}")
        return data
    except Exception as e:
        print("[CoinGecko] Exception:", e)
        if debug_message is not None:
            debug_message(f"CoinGecko Exception: {e} URL: {url}")
        return {}

# --- Chart helpers ---

async def send_portfolio_pie_chart(update, holdings, market_data):
    """
    Send a pie chart of the portfolio allocation to the user.

    Args:
        update (telegram.Update): The update object from Telegram.
        holdings (dict): The user's portfolio holdings.
        market_data (dict): The current market data for the user's coins.

    Returns:
        None
    """
    # Placeholder for async chart sending logic
    await asyncio.sleep(0)
    return None

async def send_portfolio_line_chart(update, user_id):
    """
    Send a line chart of the portfolio value over time to the user.

    Args:
        update (telegram.Update): The update object from Telegram.
        user_id (int): The user's Telegram ID.

    Returns:
        None
    """
    # Placeholder for async chart sending logic
    await asyncio.sleep(0)
    return None

# --- Add all handler logic here for modularization ---
# (Move the rest of the handler logic from cryptiq_bot.py here, e.g. settings_command, language_command, etc.)
# For now, add stubs to resolve import errors in handlers.py

async def settings_command(update, context):
    pass
async def language_command(update, context):
    pass
async def main_menu(update, context):
    pass
async def set_language(update, context):
    pass
async def language_chosen(update, context):
    pass
async def news(update, context):
    pass
async def set_alert(update, context):
    pass
async def delete_profile(update, context):
    pass
async def setbank_natural(update, context):
    pass
async def setholdings_natural(update, context):
    pass
async def set_bank(update, context):
    pass
async def set_strategy(update, context):
    pass
async def set_holdings(update, context):
    pass
async def button_handler(update, context):
    pass
async def handle_message(update, context):
    pass
async def help_command(update, context):
    pass
async def start(update, context):
    pass
async def ask_initial_questions(update, context):
    pass
async def handle_setup_answers(update, context):
    pass
async def alert_checker(app):
    pass

# Add more utility functions as needed (e.g., build_prompt, chart helpers, etc.)
