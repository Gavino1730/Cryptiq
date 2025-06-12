"""
Utility functions for Cryptiq bot (market data, error logging, prompt building, etc).
"""
import os
import json
import datetime
import requests
import pytz
import matplotlib.pyplot as plt
import io
import asyncio

# --- Error logging helper ---
def log_error(e, context=""):
    print(f"[ERROR] {context}: {e}")
    try:
        with open("error_log.json", "a") as f:
            f.write(f"{datetime.datetime.now()}: {context}: {e}\n")
    except Exception:
        pass

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
    # Placeholder for async chart sending logic
    await asyncio.sleep(0)
    return None

async def send_portfolio_line_chart(update, user_id):
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
