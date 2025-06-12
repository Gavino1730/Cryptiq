import os
import json
import requests
import asyncio
import datetime
import re
import matplotlib.pyplot as plt
import io
from typing import Any, Dict, List, Tuple, Union
import pytz
import traceback
import openai
from telegram import Update, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, JobQueue
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

# Set your tokens here
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if TELEGRAM_TOKEN is None or OPENAI_API_KEY is None:
    raise RuntimeError("TELEGRAM_TOKEN and OPENAI_API_KEY must be set as environment variables.")
TELEGRAM_TOKEN = str(TELEGRAM_TOKEN)
OPENAI_API_KEY = str(OPENAI_API_KEY)
openai.api_key = OPENAI_API_KEY

COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin%2Clitecoin&vs_currencies=usd&include_24hr_change=true"
COINGECKO_SIMPLE_PRICE_API = "https://api.coingecko.com/api/v3/simple/price?vs_currencies=usd&include_24hr_change=true&ids={ids}"
USER_DATA_FILE = os.path.join(os.path.dirname(__file__), "user_data.json")
CHAT_LOG_FILE = os.path.join(os.path.dirname(__file__), "chat_log.json")
# --- ALERTS STORAGE ---
ALERTS_FILE = os.path.join(os.path.dirname(__file__), "alerts.json")
ERROR_LOG_FILE = os.path.join(os.path.dirname(__file__), "error_log.json")

# Helper to map common coin symbols to CoinGecko IDs
COIN_SYMBOL_TO_ID = {
    'btc': 'bitcoin',
    'bitcoin': 'bitcoin',
    'ltc': 'litecoin',
    'litecoin': 'litecoin',
    # Add more mappings as needed
}

# --- Error logging helper ---
def log_error(e, context=""):
    print(f"[ERROR] {context}: {e}")
    try:
        with open(ERROR_LOG_FILE, "a") as f:
            f.write(f"{datetime.datetime.now()}: {context}: {e}\n")
    except Exception:
        pass

def load_alerts() -> Dict[str, Any]:
    try:
        with open(ALERTS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_alerts(alerts: Dict[str, Any]) -> None:
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f, indent=2)

def load_user_data(user_id: Union[str, int]) -> Dict[str, Any]:
    try:
        with open(USER_DATA_FILE, "r") as f:
            data: Dict[str, Any] = json.load(f)
        return data["users"].get(str(user_id), {})
    except Exception:
        return {}

def save_user_data(user_id: Union[str, int], user_data: Dict[str, Any]) -> None:
    try:
        with open(USER_DATA_FILE, "r") as f:
            data: Dict[str, Any] = json.load(f)
    except Exception:
        data = {"users": {}}
    data["users"][str(user_id)] = user_data
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def log_chat(user_id: Union[str, int], user_message: str, bot_response: str, portfolio_value: Union[float, None] = None) -> None:
    try:
        import pytz
        pacific = pytz.timezone('US/Pacific')
        now = datetime.datetime.now(pacific)
        now_str = now.strftime('%Y-%m-%d %I:%M %p %Z')
        if os.path.exists(CHAT_LOG_FILE):
            with open(CHAT_LOG_FILE, "r") as f:
                data = json.load(f)
        else:
            data = {"logs": {}}
        uid = str(user_id)
        if uid not in data["logs"]:
            data["logs"][uid] = []
        entry: Dict[str, Any] = {
            "timestamp": now_str,
            "user_message": user_message,
            "bot_response": bot_response
        }
        if portfolio_value is not None:
            entry["portfolio_value"] = portfolio_value
        data["logs"][uid].append(entry)
        with open(CHAT_LOG_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def get_market_data_for_coins(coin_symbols: List[str], debug_message: Union[Any, None] = None) -> Dict[str, Any]:
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

# Patch show_portfolio to surface CoinGecko errors to the user
async def show_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        print("[DEBUG] show_portfolio called")
        user_id = getattr(getattr(update, 'effective_user', None), 'id', None)
        message = getattr(update, 'message', None)
        if user_id is None or message is None:
            print("[DEBUG] show_portfolio: user_id or message is None")
            return
        user_data = load_user_data(user_id)
        if not user_data:
            print("[DEBUG] show_portfolio: No user_data")
            await message.reply_text("No portfolio found. Use /start to set up your profile.\n\nCryptiq does not offer financial advice.")
            return
        holdings = user_data.get("holdings", {})
        strategy = user_data.get("strategy", "Not set")
        coin_symbols = [k for k, v in holdings.items() if v not in (None, '', 'skip') and v is not None]
        print(f"[DEBUG] coin_symbols: {coin_symbols}")
        if not coin_symbols:
            await message.reply_text("No holdings found. Use /setholdings <coin> <amount> to add.\n\nCryptiq does not offer financial advice.")
            return
        error_msgs = []
        def debug_message(msg: str) -> None:
            error_msgs.append(msg)
        # Print ids for CoinGecko
        ids = [COIN_SYMBOL_TO_ID.get(s.lower(), s.lower()) for s in coin_symbols]
        ids = [i for i in ids if i is not None]
        print(f"[DEBUG] CoinGecko ids: {ids}")
        market_data = get_market_data_for_coins(coin_symbols, debug_message=debug_message)
        if not market_data:
            err = error_msgs[0] if error_msgs else "Could not fetch real-time data from CoinGecko. Please try again later."
            await message.reply_text(f"{err}")
            return
        total_value = 0
        holdings_str = ""
        for symbol in coin_symbols:
            coingecko_id = COIN_SYMBOL_TO_ID.get(str(symbol).lower(), str(symbol).lower())
            amount = float(holdings[symbol])
            price = float(market_data.get(str(coingecko_id), {}).get('usd', 0))
            value = amount * price
            total_value += value
            change = float(market_data.get(str(coingecko_id), {}).get('usd_24h_change', 0))
            holdings_str += f"{str(symbol).upper()}: {amount} (${'{:,}'.format(value)})  24h: {change:+.2f}%\n"
        # Try to get previous value for performance tracking
        try:
            with open(CHAT_LOG_FILE, "r") as f:
                data = json.load(f)
            user_logs = data.get("logs", {}).get(str(user_id), [])
            prev_value = None
            for entry in reversed(user_logs):
                if 'portfolio_value' in entry:
                    prev_value = entry['portfolio_value']
                    break
        except Exception:
            prev_value = None
        # Calculate performance
        perf_str = ""
        if prev_value is not None and total_value > 0:
            change = total_value - prev_value
            pct = (change / prev_value) * 100 if prev_value != 0 else 0
            arrow = "\u2191" if change > 0 else ("\u2193" if change < 0 else "")
            perf_str = f"\nPerformance since last check: {arrow} ${change:,.2f} ({pct:+.2f}%)"
        # Save current value to chat log for future performance tracking
        log_chat(user_id, "[portfolio check]", f"Portfolio value: ${total_value:,.2f}", portfolio_value=total_value)
        await message.reply_text(
            f"\U0001F4B0 Portfolio Overview:\nStrategy: {strategy}\nTotal Value: ${total_value:,.2f}{perf_str}\nHoldings:\n{holdings_str}\nCryptiq does not offer financial advice."
        )
        await send_portfolio_pie_chart(update, holdings, market_data)
        await send_portfolio_line_chart(update, user_id)
    except Exception as e:
        log_error(e, context="show_portfolio")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- SETTINGS COMMAND ---
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = getattr(update, 'effective_user', None)
        message = getattr(update, 'message', None)
        if user is None or message is None:
            return
        user_id = user.id
        user_data = load_user_data(user_id)
        lang = user_data.get('language', 'English')
        tz = user_data.get('timezone', 'US/Pacific')
        strategy = user_data.get('strategy', 'Not set')
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Change Language", callback_data='change_language')],
            [InlineKeyboardButton("Change Timezone", callback_data='change_timezone')],
            [InlineKeyboardButton("Change Strategy", callback_data='change_strategy')],
            [InlineKeyboardButton("Back to Menu", callback_data='main_menu')]
        ])
        await message.reply_text(
            f"Your Settings:\nLanguage: {lang}\nTimezone: {tz}\nStrategy: {strategy}",
            reply_markup=reply_markup
        )
    except Exception as e:
        log_error(e, context="settings_command")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- LANGUAGE COMMAND ---
async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = getattr(update, 'message', None)
        if message is None:
            return
        keyboard = [[lang] for lang in LANGUAGES.values()]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await message.reply_text('Choose your language:', reply_markup=reply_markup)
        # Set a flag in user_data to handle next message as language selection
        if hasattr(context, 'user_data') and context.user_data is not None:
            context.user_data['awaiting_language'] = True
    except Exception as e:
        log_error(e, context="language_command")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- ENHANCED MAIN MENU WITH INLINE KEYBOARD ---
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = getattr(update, 'message', None)
        if message is None:
            return
        keyboard = [
            [InlineKeyboardButton("\U0001F4B0 Portfolio", callback_data='portfolio')],
            [InlineKeyboardButton("Update Bank", callback_data='update_bank')],
            [InlineKeyboardButton("Update Holdings", callback_data='update_holdings')],
            [InlineKeyboardButton("Set Alert", callback_data='set_alert')],
            [InlineKeyboardButton("Show News", callback_data='show_news')],
            [InlineKeyboardButton("Settings", callback_data='settings')],
            [InlineKeyboardButton("Delete Profile", callback_data='delete_profile')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.reply_text('Main Menu:\n\nCryptiq does not offer financial advice.', reply_markup=reply_markup)
    except Exception as e:
        log_error(e, context="main_menu")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- MULTI-LANGUAGE SUPPORT ---
LANGUAGES = {
    'en': 'English',
    'es': 'Español',
    'fr': 'Français',
    'de': 'Deutsch',
    'it': 'Italiano',
    'ru': 'Русский',
    'zh': '中文',
    # Add more as needed
}

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from telegram import ReplyKeyboardMarkup
        message = getattr(update, 'message', None)
        if message is None:
            return
        keyboard = [[lang] for lang in LANGUAGES.values()]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await message.reply_text('Choose your language:', reply_markup=reply_markup)
    except Exception as e:
        log_error(e, context="set_language")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = getattr(update, 'message', None)
        if message is None or not hasattr(message, 'text'):
            return
        chosen = message.text
        for code, name in LANGUAGES.items():
            if chosen == name:
                user_id = getattr(getattr(update, 'effective_user', None), 'id', None)
                if user_id is None:
                    return
                user_data = load_user_data(user_id)
                user_data['language'] = code
                save_user_data(user_id, user_data)
                await message.reply_text(f'Language set to {name}.')
                return
        await message.reply_text('Language not recognized.')
    except Exception as e:
        log_error(e, context="language_chosen")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- ADVANCED ANALYTICS & INSIGHTS ---
async def analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = getattr(getattr(update, 'effective_user', None), 'id', None)
        message = getattr(update, 'message', None)
        if user_id is None or message is None:
            return
        user_data = load_user_data(user_id)
        holdings = user_data.get("holdings", {})
        if not holdings:
            await message.reply_text("No holdings found.")
            return
        # Filter out None, non-numeric, or non-positive holdings
        coin_symbols = [k for k, v in holdings.items() if v not in (None, '', 'skip')]
        coin_symbols = [k for k in coin_symbols if isinstance(holdings[k], (int, float)) and holdings[k] > 0]
        if not coin_symbols:
            await message.reply_text("No holdings found.")
            return
        ids = [COIN_SYMBOL_TO_ID.get(s.lower(), s.lower()) for s in coin_symbols]
        ids = [i for i in ids if i is not None]
        ids_str = '%2C'.join(ids)
        url = f"https://api.coingecko.com/api/v3/simple/price?vs_currencies=usd&include_7d_change=true&ids={ids_str}"
        try:
            resp = requests.get(url)
            data = resp.json()
            best = None
            worst = None
            for symbol in coin_symbols:
                coingecko_id = COIN_SYMBOL_TO_ID.get(str(symbol).lower(), str(symbol).lower())
                change = data.get(coingecko_id, {}).get('usd_7d_change', 0)
                if best is None or change > best[1]:
                    best = (symbol, change)
                if worst is None or change < worst[1]:
                    worst = (symbol, change)
            if best and worst:
                msg = f"Best performer this week: {best[0].upper()} ({best[1]:+.2f}%)\nWorst performer: {worst[0].upper()} ({worst[1]:+.2f}%)"
            else:
                msg = "Not enough data for analytics."
            await message.reply_text(msg)
        except Exception:
            await message.reply_text("Could not fetch analytics.")
    except Exception as e:
        log_error(e, context="analytics")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

async def risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = getattr(getattr(update, 'effective_user', None), 'id', None)
        message = getattr(update, 'message', None)
        if user_id is None or message is None:
            return
        user_data = load_user_data(user_id)
        holdings = user_data.get("holdings", {})
        if not holdings:
            await message.reply_text("No holdings found.")
            return
        # Filter out None, non-numeric, or non-positive holdings
        coin_symbols = [k for k, v in holdings.items() if v not in (None, '', 'skip')]
        coin_symbols = [k for k in coin_symbols if isinstance(holdings[k], (int, float)) and holdings[k] > 0]
        market_data = get_market_data_for_coins(coin_symbols)
        values = []
        for symbol in coin_symbols:
            coingecko_id = COIN_SYMBOL_TO_ID.get(str(symbol).lower(), str(symbol).lower())
            amount = float(holdings[symbol])
            price = float(market_data.get(str(coingecko_id), {}).get('usd', 0))
            values.append(amount * price)
        total = sum(values)
        if total == 0:
            await message.reply_text("No holdings value found.")
            return
        largest = max(values)
        risk_score = (largest / total) * 100
        await message.reply_text(f"Risk score (largest allocation): {risk_score:.1f}%\nLower is better for diversification.")
    except Exception as e:
        log_error(e, context="risk")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

async def backtest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = getattr(getattr(update, 'effective_user', None), 'id', None)
        message = getattr(update, 'message', None)
        if user_id is None or message is None:
            return
        user_data = load_user_data(user_id)
        holdings = user_data.get("holdings", {})
        if not holdings:
            await message.reply_text("No holdings found.")
            return
        days = 30
        args = getattr(context, 'args', None)
        if args and len(args) > 0:
            try:
                days = int(args[0])
            except Exception:
                pass
        # Filter out None, non-numeric, or non-positive holdings
        coin_symbols = [k for k, v in holdings.items() if v not in (None, '', 'skip')]
        coin_symbols = [k for k in coin_symbols if isinstance(holdings[k], (int, float)) and holdings[k] > 0]
        ids = [COIN_SYMBOL_TO_ID.get(s.lower(), s.lower()) for s in coin_symbols]
        ids = [i for i in ids if i is not None]
        ids_str = '%2C'.join(ids)
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={ids_str}&price_change_percentage={days}d"
        try:
            resp = requests.get(url)
            data = resp.json()
            start_value = 0
            end_value = 0
            for coin in data:
                symbol = coin['symbol']
                coingecko_id = coin['id']
                amount = holdings.get(symbol, holdings.get(coingecko_id, 0))
                if not amount or not isinstance(amount, (int, float)) or amount <= 0:
                    continue
                price = float(coin['current_price'])
                pct = coin.get(f'price_change_percentage_{days}d_in_currency', 0)
                old_price = price / (1 + pct/100) if pct else price
                start_value += float(amount) * old_price
                end_value += float(amount) * price
            if start_value == 0:
                await message.reply_text("No historical data found.")
                return
            change = end_value - start_value
            pct = (change / start_value) * 100
            await message.reply_text(f"Backtest ({days}d): Portfolio change: ${change:,.2f} ({pct:+.2f}%)")
        except Exception:
            await message.reply_text("Could not fetch backtest data.")
    except Exception as e:
        log_error(e, context="backtest")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- PORTFOLIO PIE CHART ---
async def send_portfolio_pie_chart(
    update: Any,
    holdings: Dict[str, Union[int, float, None]],
    market_data: Dict[str, Dict[str, float]]
) -> None:
    try:
        labels: List[str] = []
        sizes: List[float] = []
        def is_valid_amount(val: Any) -> bool:
            try:
                return val is not None and float(val) > 0
            except Exception:
                return False
        for symbol, amount in holdings.items():
            if not is_valid_amount(amount):
                continue
            coingecko_id = COIN_SYMBOL_TO_ID.get(str(symbol).lower(), str(symbol).lower())
            price = float(market_data.get(str(coingecko_id), {}).get('usd', 0))
            try:
                if amount is None:
                    continue
                value = float(amount) * price
            except Exception:
                continue
            if value > 0:
                labels.append(str(symbol).upper())
                sizes.append(value)
        if not sizes:
            return
        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, autopct='%1.1f%%')
        ax.set_title('Portfolio Allocation')
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        if hasattr(update, 'message') and getattr(update, 'message', None):
            await update.message.reply_photo(photo=buf)
        plt.close(fig)
    except Exception as e:
        log_error(e, context="send_portfolio_pie_chart")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- PORTFOLIO LINE CHART ---
def get_portfolio_history(user_id: Union[str, int]) -> List[Tuple[str, float]]:
    try:
        with open(CHAT_LOG_FILE, "r") as f:
            data = json.load(f)
        user_logs = data.get("logs", {}).get(str(user_id), [])
        # Get user's timezone if available
        user_profile = load_user_data(user_id)
        tz_str = user_profile.get('timezone', 'UTC')
        try:
            tz = pytz.timezone(tz_str)
        except Exception:
            tz = pytz.UTC
        history = []
        for entry in user_logs:
            if "portfolio_value" in entry:
                # Convert timestamp to user's timezone
                try:
                    dt = datetime.datetime.fromisoformat(entry["timestamp"])
                    if dt.tzinfo is None:
                        dt = pytz.UTC.localize(dt)
                    dt = dt.astimezone(tz)
                    history.append((dt.isoformat(), float(entry["portfolio_value"])))
                except Exception:
                    continue
        return history
    except Exception:
        return []

async def send_portfolio_line_chart(update: Any, user_id: Union[str, int]) -> None:
    try:
        import matplotlib.dates as mdates
        history = get_portfolio_history(user_id)
        if len(history) < 2:
            return
        try:
            dates = [datetime.datetime.fromisoformat(ts) for ts, _ in history]
            values = [float(v) for _, v in history]
        except Exception:
            return
        # Get user's timezone for x-axis label
        user_profile = load_user_data(user_id)
        tz_str = user_profile.get('timezone', 'UTC')
        try:
            tz = pytz.timezone(tz_str)
        except Exception:
            tz = pytz.UTC
        tz_label = tz_str
        dates_num = mdates.date2num(dates)
        fig, ax = plt.subplots()
        ax.plot_date(dates_num, values, marker='o', linestyle='-')
        ax.set_title('Portfolio Value Over Time')
        ax.set_xlabel(f'Date ({tz_label})')
        ax.set_ylabel('USD Value')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d', tz=tz))
        fig.autofmt_xdate()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        if hasattr(update, 'message') and getattr(update, 'message', None):
            await update.message.reply_photo(photo=buf)
        plt.close(fig)
    except Exception as e:
        log_error(e, context="send_portfolio_line_chart")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- ENHANCED MAIN ---
async def delete_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = getattr(update, 'effective_user', None)
        message = getattr(update, 'message', None)
        if user is None or message is None:
            return
        user_id = user.id
        try:
            with open(USER_DATA_FILE, "r") as f:
                data = json.load(f)
            if str(user_id) in data.get("users", {}):
                del data["users"][str(user_id)]
                with open(USER_DATA_FILE, "w") as f2:
                    json.dump(data, f2, indent=2)
                await message.reply_text("Your profile and portfolio have been deleted.\n\nCryptiq does not offer financial advice.")
            else:
                await message.reply_text("No profile found to delete.\n\nCryptiq does not offer financial advice.")
        except Exception:
            await message.reply_text("Error deleting profile.\n\nCryptiq does not offer financial advice.")
    except Exception as e:
        log_error(e, context="delete_profile")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- ENHANCED MAIN ---

async def setbank_natural(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        import re
        user = getattr(update, 'effective_user', None)
        message = getattr(update, 'message', None)
        if user is None or message is None or not hasattr(message, 'text'):
            return
        user_id = user.id
        text = message.text
        match = re.search(r'(\$?\d+[\d,\.]*\d*)', text)
        if match:
            try:
                amount = float(match.group(1).replace('$','').replace(',',''))
                user_data = load_user_data(user_id)
                user_data["bank"] = amount
                save_user_data(user_id, user_data)
                await message.reply_text(f"Bank balance set to ${amount:,.2f}.\n\nCryptiq does not offer financial advice.")
            except Exception:
                await message.reply_text("Could not parse the amount. Try again.\n\nCryptiq does not offer financial advice.")
        else:
            await message.reply_text("Please include a number in your message.\n\nCryptiq does not offer financial advice.")
    except Exception as e:
        log_error(e, context="setbank_natural")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

async def setholdings_natural(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        import re
        user = getattr(update, 'effective_user', None)
        message = getattr(update, 'message', None)
        if user is None or message is None or not hasattr(message, 'text'):
            return
        user_id = user.id
        text = message.text.lower()
        match = re.search(r'(\w+)[\s:=,]*([\d\.]+)', text)
        if match:
            coin = match.group(1)
            try:
                amount = float(match.group(2).replace(',', ''))
                user_data = load_user_data(user_id)
                if "holdings" not in user_data:
                    user_data["holdings"] = {}
                user_data["holdings"][coin] = amount
                save_user_data(user_id, user_data)
                await message.reply_text(f"Set {coin.upper()} holdings to {amount}.\n\nCryptiq does not offer financial advice.")
            except Exception:
                await message.reply_text("Could not parse the amount. Try again.\n\nCryptiq does not offer financial advice.")
        else:
            await handle_message(update, context)
    except Exception as e:
        log_error(e, context="setholdings_natural")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

async def set_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = getattr(update, 'effective_user', None)
        message = getattr(update, 'message', None)
        args = getattr(context, 'args', None)
        if user is None or message is None or not args or len(args) < 1:
            if message is not None:
                await message.reply_text("Usage: /setbank <amount>\n\nCryptiq does not offer financial advice.")
            return
        try:
            amount = float(args[0])
            user_id = user.id
            user_data = load_user_data(user_id)
            user_data["bank"] = amount
            save_user_data(user_id, user_data)
            await message.reply_text(f"Bank balance set to ${amount:,.2f}.\n\nCryptiq does not offer financial advice.")
        except Exception:
            if message is not None:
                await message.reply_text("Usage: /setbank <amount>\n\nCryptiq does not offer financial advice.")
    except Exception as e:
        log_error(e, context="set_bank")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

async def set_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = getattr(update, 'effective_user', None)
        message = getattr(update, 'message', None)
        args = getattr(context, 'args', None)
        if user is None or message is None or not args:
            return
        strategy = " ".join(args)
        user_id = user.id
        user_data = load_user_data(user_id)
        user_data["strategy"] = strategy
        save_user_data(user_id, user_data)
        await message.reply_text("Strategy updated.\n\nCryptiq does not offer financial advice.")
    except Exception as e:
        log_error(e, context="set_strategy")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

async def set_holdings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = getattr(update, 'effective_user', None)
        message = getattr(update, 'message', None)
        args = getattr(context, 'args', None)
        if user is None or message is None or not args or len(args) < 2:
            if message is not None:
                await message.reply_text("Usage: /setholdings <coin> <amount>\n\nCryptiq does not offer financial advice.")
            return
        try:
            coin = args[0].lower()
            amount = float(args[1])
            user_id = user.id
            user_data = load_user_data(user_id)
            if "holdings" not in user_data:
                user_data["holdings"] = {}
            user_data["holdings"][coin] = amount
            save_user_data(user_id, user_data)
            await message.reply_text(f"Set {coin.upper()} holdings to {amount}.\n\nCryptiq does not offer financial advice.")
        except Exception:
            if message is not None:
                await message.reply_text("Usage: /setholdings <coin> <amount>\n\nCryptiq does not offer financial advice.")
    except Exception as e:
        log_error(e, context="set_holdings")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

async def set_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = getattr(update, 'effective_user', None)
        message = getattr(update, 'message', None)
        args = getattr(context, 'args', None)
        if user is None or message is None or not args or len(args) < 2:
            if message is not None:
                await message.reply_text("Usage: /setalert <coin> <price>\nExample: /setalert btc 70000\n\nCryptiq does not offer financial advice.")
            return
        try:
            coin = args[0].lower()
            price = float(args[1])
            user_id = str(user.id)
            alerts = load_alerts()
            if user_id not in alerts:
                alerts[user_id] = []
            alerts[user_id].append({"coin": coin, "price": price})
            save_alerts(alerts)
            await message.reply_text(f"Alert set for {coin.upper()} at ${price:,.2f}.\n\nCryptiq does not offer financial advice.")
        except Exception:
            if message is not None:
                await message.reply_text("Usage: /setalert <coin> <price>\nExample: /setalert btc 70000\n\nCryptiq does not offer financial advice.")
    except Exception as e:
        log_error(e, context="set_alert")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = getattr(update, 'message', None)
        if message is None:
            return
        NEWS_API = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        try:
            resp = requests.get(NEWS_API)
            data = resp.json()
            articles = data.get('Data', [])[:5]
            if not articles:
                await message.reply_text("No news found.\n\nCryptiq does not offer financial advice.")
                return
            msg = "\U0001F4F0 Latest Crypto News:\n"
            for a in articles:
                msg += f"\n• <a href='{a['url']}'>{a['title']}</a>"
            await message.reply_text(msg, parse_mode='HTML')
        except Exception:
            await message.reply_text("Could not fetch news.\n\nCryptiq does not offer financial advice.")
    except Exception as e:
        log_error(e, context="news")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- Refactor button_handler to avoid passing CallbackQuery to Update handlers ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = getattr(update, 'callback_query', None)
        if query is None:
            return
        await query.answer()
        if query.data == 'portfolio':
            # Simulate an Update for show_portfolio (effective_user is inferred from message)
            from telegram import Update as TgUpdate
            fake_update = TgUpdate(update.update_id, message=query.message)
            await show_portfolio(fake_update, context)
        elif query.data == 'update_bank':
            await query.edit_message_text("Send me your new bank balance (e.g., $5000 or 5000)\n\nCryptiq does not offer financial advice.")
        elif query.data == 'update_holdings':
            await query.edit_message_text("Send me your new holdings (e.g., BTC 0.5 or LTC 2.0)\n\nCryptiq does not offer financial advice.")
        elif query.data == 'set_alert':
            await query.edit_message_text("Use /setalert <coin> <price> to set a price alert.\n\nCryptiq does not offer financial advice.")
        elif query.data == 'show_news':
            from telegram import Update as TgUpdate
            fake_update = TgUpdate(update.update_id, message=query.message)
            await news(fake_update, context)
        elif query.data == 'settings':
            from telegram import Update as TgUpdate
            fake_update = TgUpdate(update.update_id, message=query.message)
            await settings_command(fake_update, context)
        elif query.data == 'change_language':
            from telegram import Update as TgUpdate
            fake_update = TgUpdate(update.update_id, message=query.message)
            await language_command(fake_update, context)
        elif query.data == 'main_menu':
            from telegram import Update as TgUpdate
            fake_update = TgUpdate(update.update_id, message=query.message)
            await main_menu(fake_update, context)
        elif query.data == 'delete_profile':
            from telegram import Update as TgUpdate
            fake_update = TgUpdate(update.update_id, message=query.message)
            await delete_profile(fake_update, context)
    except Exception as e:
        log_error(e, context="button_handler")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- Robust handle_message ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_data_dict = getattr(context, 'user_data', None)
        if user_data_dict is None:
            return
        # If user is in language selection mode, call language_chosen
        if user_data_dict.get('awaiting_language'):
            await language_chosen(update, context)
            return
        if user_data_dict.get('setup_step') is not None:
            await handle_setup_answers(update, context)
            return
        message = getattr(update, 'message', None)
        user = getattr(update, 'effective_user', None)
        if message is None or user is None or not hasattr(message, 'text'):
            return
        user_message = message.text
        user_id = user.id
        user_data = load_user_data(user_id)
        holdings = user_data.get("holdings", {})
        coin_symbols = [k for k, v in holdings.items() if v not in (None, '', 'skip') and v is not None]
        if coin_symbols:
            market_data = get_market_data_for_coins(coin_symbols)
        else:
            market_data = {}
        btc = market_data.get('bitcoin', {'usd': 0, 'usd_24h_change': 0})
        ltc = market_data.get('litecoin', {'usd': 0, 'usd_24h_change': 0})
        chat_history = []
        try:
            with open(CHAT_LOG_FILE, "r") as f:
                data = json.load(f)
            user_logs = data.get("logs", {}).get(str(user_id), [])
            # Only include the last 5 exchanges for context
            for entry in user_logs[-5:]:
                chat_history.append({"role": "user", "content": entry["user_message"]})
                chat_history.append({"role": "assistant", "content": entry["bot_response"]})
        except Exception:
            pass
        chat_history.append({"role": "user", "content": build_prompt(user_message, btc, ltc, user_data)})
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=chat_history,
                max_tokens=500,
                temperature=0.7
            )
            def clean_markdown(text: str) -> str:
                text = text.replace('###', '').replace('**', '').replace('-', '•')
                return text
            content = response.choices[0].message.content if response.choices and response.choices[0].message and response.choices[0].message.content else None
            if content:
                answer = clean_markdown(content.strip())
            else:
                answer = "Sorry, there was an error with the AI service.\n\nCryptiq does not offer financial advice."
            answer = f"{answer}\n\nCryptiq does not offer financial advice."
        except Exception as e:
            print(f"OpenAI API error: {e}")
            answer = f"Sorry, there was an error with the AI service: {e}\n\nCryptiq does not offer financial advice."
        if message is not None:
            await message.reply_text(answer)
        log_chat(user_id, user_message, answer)
    except Exception as e:
        log_error(e, context="handle_message")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- Add help_command ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = getattr(update, 'message', None)
        if message is None:
            return
        await message.reply_text(
            "Available commands:\n"
            "/start - Start or reset your profile\n"
            "/portfolio - Show your portfolio\n"
            "/setbank <amount> - Set your bank balance\n"
            "/setholdings <coin> <amount> - Set holdings\n"
            "/setstrategy <strategy> - Set your trading strategy\n"
            "/setalert <coin> <price> - Set a price alert\n"
            "/news - Show latest crypto news\n"
            "/deleteprofile - Delete your profile\n"
            "/menu - Show main menu\n"
            "\nCryptiq does not offer financial advice."
        )
    except Exception as e:
        log_error(e, context="help_command")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

async def alert_checker(app: Any) -> None:
    while True:
        alerts = load_alerts()
        if not alerts:
            await asyncio.sleep(60)
            continue
        # Collect all coins to check
        coins = set()
        for user_alerts in alerts.values():
            for alert in user_alerts:
                coins.add(alert['coin'])
        market_data = get_market_data_for_coins(list(coins))
        # Check alerts
        to_remove = {}
        for user_id, user_alerts in alerts.items():
            # Get Pacific time for alert time
            try:
                import pytz
                pacific = pytz.timezone('US/Pacific')
                now = datetime.datetime.now(pacific)
                now_str = now.strftime('%Y-%m-%d %I:%M %p %Z')
            except Exception:
                now_str = datetime.datetime.utcnow().strftime('%Y-%m-%d %I:%M %p UTC')
            for alert in user_alerts:
                coin = alert['coin']
                price = alert['price']
                coingecko_id = COIN_SYMBOL_TO_ID.get(coin, coin)
                current = float(market_data.get(str(coingecko_id), {}).get('usd', 0))
                if current is not None and ((current >= price) or (current <= price)):
                    # Notify user with Pacific time
                    try:
                        await app.bot.send_message(
                            chat_id=int(user_id),
                            text=(
                                f"Alert: {coin.upper()} has reached ${current:,.2f} (target: ${price:,.2f})!\n"
                                f"Time: {now_str}\n\nCryptiq does not offer financial advice."
                            )
                        )
                    except Exception:
                        pass
                    # Mark for removal
                    to_remove.setdefault(str(user_id), []).append(alert)
        # Remove triggered alerts
        for user_id, alerts_list in to_remove.items():
            for alert in alerts_list:
                alerts[user_id].remove(alert)
            if not alerts[user_id]:
                del alerts[user_id]
        save_alerts(alerts)
        await asyncio.sleep(60)  # Check every 60 seconds

def build_prompt(user_message: str, btc: Dict[str, Any], ltc: Dict[str, Any], user_data: Union[Dict[str, Any], None] = None) -> str:
    user_info = ""
    if user_data:
        bank = user_data.get("bank", "Not set")
        strategy = user_data.get("strategy", "Not set")
        holdings = user_data.get("holdings", {})
        holdings_str = ", ".join(f"{k.upper()}: {v}" for k, v in holdings.items()) if holdings else "None"
        user_info = f"\nUser Bank: ${bank}\nUser Strategy: {strategy}\nUser Holdings: {holdings_str}\n"
    prompt = f"""
You are a crypto trading expert AI. Be concise and direct. When asked for a prediction, always give a specific price target. When asked where to buy or sell, always give a concrete price (even if it's an estimate). Give reasoning after estimates. Avoid long explanations. Use the following real-time data:

Bitcoin: Price ${btc['usd']}, 24h Change {btc['usd_24h_change']:.2f}%
Litecoin: Price ${ltc['usd']}, 24h Change {ltc['usd_24h_change']:.2f}%
{user_info}
User: {user_message}
AI:
"""
    return prompt

# --- Add missing import for start handler ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = getattr(update, 'effective_user', None)
        message = getattr(update, 'message', None)
        if user is None or message is None:
            return
        user_id = user.id
        user_data = load_user_data(user_id)
        if not user_data:
            await ask_initial_questions(update, context)
        else:
            # Show main menu with buttons for existing users
            await main_menu(update, context)
    except Exception as e:
        log_error(e, context="start")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- Enhanced onboarding: ask BTC, then ask for other coins, then ask for each amount ---
async def ask_initial_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message = getattr(update, 'message', None)
        user_data = getattr(context, 'user_data', None)
        if message is None or user_data is None:
            return
        await message.reply_text(
            "Welcome to Cryptiq! I'm your AI crypto assistant. I provide market analysis, predictions, and portfolio advice for all cryptocurrencies.\n\nYour data is kept private and secure, stored only for your use.\n\nLet's set up your profile. You can skip any question by clicking 'Skip'.\n\nCryptiq does not offer financial advice."
        )
        user_data['setup_step'] = 0
        user_data['setup_answers'] = {}
        await handle_setup_answers(update, context)
    except Exception as e:
        log_error(e, context="ask_initial_questions")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

async def handle_setup_answers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message = getattr(update, 'message', None)
        user_data = getattr(context, 'user_data', None)
        if message is None or user_data is None:
            return
        step = user_data.get('setup_step', 0)
        answers = user_data.get('setup_answers', {})
        text = message.text.strip() if hasattr(message, 'text') and message.text else ''
        print(f"[ONBOARDING] Step: {step}, Text: {text}, Answers: {answers}")
        # Step 0: Ask if user owns any crypto
        if step == 0 and not answers:
            user_data['setup_step'] = 1
            user_data['setup_answers'] = answers
            print("[ONBOARDING] Asking if user owns crypto")
            await message.reply_text("Do you own any crypto? (yes/no/skip)\nExample: yes")
            return
        # Save answer for previous step
        if step > 0:
            answers[step - 1] = text
        # Step 1: If user said yes, ask for BTC, else skip to strategy
        if step == 1:
            owns_crypto = answers.get(0, '').lower()
            if owns_crypto in ['yes', 'y']:
                user_data['setup_step'] = 2
                user_data['setup_answers'] = answers
                print("[ONBOARDING] Asking for BTC amount")
                await message.reply_text("How much Bitcoin (BTC) do you currently own? (Reply with just the number or type 'skip')\nExample: 0.5")
                return
            else:
                user_data['setup_step'] = 100
                user_data['setup_answers'] = answers
                print("[ONBOARDING] Skipping to strategy question")
                await message.reply_text("What is your main trading strategy? (HODL, Swing trading, Day trading, Other, or Skip)\nExample: HODL")
                return
        # Step 2: Ask for other coins
        if step == 2:
            user_data['setup_step'] = 3
            user_data['setup_answers'] = answers
            print("[ONBOARDING] Asking for other coins")
            await message.reply_text("What other cryptocurrencies do you own? (List symbols separated by commas, or type 'none' or 'skip')\nExample: ETH, LTC, DOGE")
            return
        # Step 3: Parse other coins and start asking for their amounts
        if step == 3:
            raw = answers.get(2, '').strip()
            if raw.lower() == 'none' or not raw:
                user_data['other_symbols'] = []
                user_data['setup_step'] = 100
                user_data['setup_answers'] = answers
                print("[ONBOARDING] No other coins, skipping to strategy")
                await message.reply_text("What is your main trading strategy? (HODL, Swing trading, Day trading, Other, or Skip)\nExample: HODL")
                return
            symbols = [s.strip().lower() for s in raw.split(',') if s.strip() and s.strip().lower() != 'btc']
            user_data['other_symbols'] = symbols
            user_data['other_symbol_index'] = 0
            if not symbols:
                user_data['setup_step'] = 100
                user_data['setup_answers'] = answers
                print("[ONBOARDING] No valid other coins, skipping to strategy")
                await message.reply_text("What is your main trading strategy? (HODL, Swing trading, Day trading, Other, or Skip)\nExample: HODL")
                return
            user_data['setup_step'] = 4
            user_data['setup_answers'] = answers
            symbol = symbols[0]
            print(f"[ONBOARDING] Asking for amount of {symbol}")
            await message.reply_text(f"How much {symbol.upper()} do you currently own? (Reply with just the number or type 'skip')\nExample: 2.0")
            return
        # Step 4+: For each symbol, ask for amount
        if step >= 4 and 'other_symbols' in user_data:
            idx = user_data.get('other_symbol_index', 0)
            symbols = user_data.get('other_symbols', [])
            if idx < len(symbols):
                # Validate input
                if text.lower() != 'skip':
                    try:
                        float(text)
                    except Exception:
                        await message.reply_text(f"Please enter a valid number for {symbols[idx].upper()} (or type 'skip'). Example: 2.0")
                        return
                answers[f'other_{symbols[idx]}'] = text
                idx += 1
                if idx < len(symbols):
                    user_data['other_symbol_index'] = idx
                    user_data['setup_step'] = step + 1
                    user_data['setup_answers'] = answers
                    symbol = symbols[idx]
                    print(f"[ONBOARDING] Asking for amount of {symbol}")
                    await message.reply_text(f"How much {symbol.upper()} do you currently own? (Reply with just the number or type 'skip')\nExample: 2.0")
                    return
                else:
                    user_data['setup_step'] = 100
                    user_data['setup_answers'] = answers
                    user_data['other_symbol_index'] = None
                    print("[ONBOARDING] Finished all other coins, moving to strategy")
                    await message.reply_text("What is your main trading strategy? (HODL, Swing trading, Day trading, Other, or Skip)\nExample: HODL")
                    return
        # Step 100: Ask for strategy
        if step == 100:
            user_data['setup_step'] = 101
            user_data['setup_answers'] = answers
            print("[ONBOARDING] Asking for risk tolerance")
            await message.reply_text("How much are you willing to risk per trade? (Low 1–2%, Medium 3–5%, High 5–10%, or Skip)\nExample: Low 1–2%")
            return
        # Step 101: Ask for risk tolerance
        if step == 101:
            user_data['setup_step'] = 102
            user_data['setup_answers'] = answers
            print("[ONBOARDING] Asking for time horizon")
            await message.reply_text("How long do you plan to hold your position? (Hours, Days, Weeks, Months or longer, or Skip)\nExample: Months or longer")
            return
        # Step 102: Ask for time horizon
        if step == 102:
            user_data['setup_step'] = 103
            user_data['setup_answers'] = answers
            print("[ONBOARDING] Asking for experience")
            await message.reply_text("What is your level of trading experience? (Beginner, Intermediate, Advanced, or Skip)\nExample: Beginner")
            return
        # Step 103: Ask for timezone
        if step == 103:
            user_data['setup_step'] = 104
            user_data['setup_answers'] = answers
            print("[ONBOARDING] Asking for timezone")
            await message.reply_text("What is your timezone? (e.g., UTC, UTC+2, America/Los_Angeles, America/New_York, Europe/London, or Skip)\nExample: America/Los_Angeles")
            return
        # Step 104: Save profile and finish
        if step == 104:
            answers[104] = text
            user = getattr(update, 'effective_user', None)
            if user is not None:
                user_id = user.id
                # Build holdings dict
                holdings = {}
                btc_amt = answers.get(1, None)
                if btc_amt and btc_amt.lower() != 'skip':
                    try:
                        holdings['btc'] = float(btc_amt)
                    except Exception:
                        pass
                # Add other coins
                for k in answers:
                    if str(k).startswith('other_'):
                        symbol = k.replace('other_', '')
                        amt = answers[k]
                        if amt and amt.lower() != 'skip':
                            try:
                                holdings[symbol] = float(amt)
                            except Exception:
                                pass
                # Save user profile
                profile = {
                    'holdings': holdings,
                    'strategy': answers.get(100, ''),
                    'risk_tolerance': answers.get(101, ''),
                    'time_horizon': answers.get(102, ''),
                    'experience': answers.get(103, ''),
                    'timezone': answers.get(104, 'US/Pacific')
                }
                save_user_data(user_id, profile)
                await message.reply_text(
                    "Profile setup complete! You can now use all features. Type /menu to open the main menu with buttons, or /help for commands.\n\nCryptiq does not offer financial advice."
                )
                # Show main menu with buttons after onboarding
                await main_menu(update, context)
                # Clean up onboarding keys
                for k in ['setup_step', 'setup_answers', 'other_symbols', 'other_symbol_index']:
                    if k in user_data:
                        user_data[k] = None
                print("[ONBOARDING] Onboarding complete and cleaned up user_data")
    except Exception as e:
        log_error(e, context="handle_setup_answers")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- MAIN ENTRY POINT: Add new handlers ---
def main():
    import logging
    from telegram.ext import Application, JobQueue
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    job_queue = JobQueue()
    app = Application.builder().token(TELEGRAM_TOKEN).job_queue(job_queue).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("portfolio", show_portfolio))
    app.add_handler(CommandHandler("setbank", set_bank))
    app.add_handler(CommandHandler("setholdings", set_holdings))
    app.add_handler(CommandHandler("setstrategy", set_strategy))
    app.add_handler(CommandHandler("setalert", set_alert))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("deleteprofile", delete_profile))
    app.add_handler(CommandHandler("menu", main_menu))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    # Start alert checker in background
    async def alert_checker_job(context):
        await alert_checker(app)
    job_queue.run_repeating(alert_checker_job, interval=60, first=0)
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
