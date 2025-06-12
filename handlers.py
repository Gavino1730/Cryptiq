"""
handlers.py

Telegram command and message handlers for Cryptiq bot.
Each handler function responds to a specific command, message, or button press from the user.
Handlers use utility and database modules for business logic and persistence.
"""
from telegram import Update, ForceReply
from telegram.ext import ContextTypes
import database
import utils
import keyboards
import json  # Ensure json is imported for file operations

# Example handler with detailed docstring:
# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """
#     /start command handler. Begins onboarding or shows main menu for existing users.
#     """
#     ...

# --- Handler functions ---
# All handler functions from cryptiq_bot.py are moved here.
# Imports from utils/database/keyboards are used for data and helpers.

# --- Portfolio and analytics handlers ---
async def show_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /portfolio command handler. Shows the user's crypto portfolio value, holdings, and performance.
    """
    try:
        user_id = getattr(getattr(update, 'effective_user', None), 'id', None)
        message = getattr(update, 'message', None)
        if user_id is None or message is None:
            return
        user_data = database.load_user_data(user_id)
        if not user_data:
            await message.reply_text("No portfolio found. Use /start to set up your profile.\n\nCryptiq does not offer financial advice.")
            return
        holdings = user_data.get("holdings", {})
        strategy = user_data.get("strategy", "Not set")
        coin_symbols = [k for k, v in holdings.items() if v not in (None, '', 'skip') and v is not None]
        if not coin_symbols:
            await message.reply_text("No holdings found. Use /setholdings <coin> <amount> to add.\n\nCryptiq does not offer financial advice.")
            return
        error_msgs = []
        def debug_message(msg: str) -> None:
            error_msgs.append(msg)
        market_data = utils.get_market_data_for_coins(coin_symbols, debug_message=debug_message)
        if not market_data:
            err = error_msgs[0] if error_msgs else "Could not fetch real-time data from CoinGecko. Please try again later."
            await message.reply_text(f"{err}")
            return
        total_value = 0
        holdings_str = ""
        for symbol in coin_symbols:
            coingecko_id = utils.COIN_SYMBOL_TO_ID.get(str(symbol).lower(), str(symbol).lower())
            amount = float(holdings[symbol])
            price = float(market_data.get(str(coingecko_id), {}).get('usd', 0))
            value = amount * price
            total_value += value
            change = float(market_data.get(str(coingecko_id), {}).get('usd_24h_change', 0))
            holdings_str += f"{str(symbol).upper()}: {amount} (${'{:,}'.format(value)})  24h: {change:+.2f}%\n"
        # Try to get previous value for performance tracking
        try:
            with open(database.CHAT_LOG_FILE, "r") as f:
                data = json.load(f)
            user_logs = data.get("logs", {}).get(str(user_id), [])
            prev_value = None
            for entry in reversed(user_logs):
                if 'portfolio_value' in entry:
                    prev_value = entry['portfolio_value']
                    break
        except Exception:
            prev_value = None
        perf_str = ""
        if prev_value is not None and total_value > 0:
            change = total_value - prev_value
            pct = (change / prev_value) * 100 if prev_value != 0 else 0
            arrow = "\u2191" if change > 0 else ("\u2193" if change < 0 else "")
            perf_str = f"\nPerformance since last check: {arrow} ${change:,.2f} ({pct:+.2f}%)"
        database.log_chat(user_id, "[portfolio check]", f"Portfolio value: ${total_value:,.2f}", portfolio_value=total_value)
        await message.reply_text(
            f"\U0001F4B0 Portfolio Overview:\nStrategy: {strategy}\nTotal Value: ${total_value:,.2f}{perf_str}\nHoldings:\n{holdings_str}\nCryptiq does not offer financial advice."
        )
        await utils.send_portfolio_pie_chart(update, holdings, market_data)
        await utils.send_portfolio_line_chart(update, user_id)
    except Exception as e:
        utils.log_error(e, context="show_portfolio")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- Settings, language, and menu handlers ---
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /settings command handler. Shows the user current settings and options to change them.
    """
    return await utils.settings_command(update, context)

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /language command handler. Displays available languages and current language setting.
    """
    return await utils.language_command(update, context)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /menu command handler. Shows the main menu with available actions for the user.
    """
    return await utils.main_menu(update, context)

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    set_language handler. Updates the user's language preference.
    """
    return await utils.set_language(update, context)

async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    language_chosen handler. Confirms and applies the user's language choice.
    """
    return await utils.language_chosen(update, context)

# --- News, alerts, and profile handlers ---
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    news handler. Sends the latest crypto news to the user, with error handling.
    """
    try:
        message = getattr(update, 'message', None)
        if message is None:
            return
        NEWS_API = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        try:
            resp = utils.requests.get(NEWS_API)
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
        utils.log_error(e, context="news")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

async def set_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    set_alert handler. Creates or updates a price alert for a specific cryptocurrency with input validation.
    """
    try:
        user = getattr(update, 'effective_user', None)
        message = getattr(update, 'message', None)
        args = getattr(context, 'args', None)
        if user is None or message is None or not args or len(args) < 2:
            if message is not None:
                await message.reply_text("Usage: /setalert <coin> <price>\nExample: /setalert btc 70000\n\nCryptiq does not offer financial advice.")
            return
        coin = args[0].lower()
        try:
            price = float(args[1])
            if price < 0 or price > 1e7:
                await message.reply_text("Please enter a valid, positive price (less than 10 million).\n\nCryptiq does not offer financial advice.")
                return
        except Exception:
            await message.reply_text("Usage: /setalert <coin> <price> (price must be a number)\n\nCryptiq does not offer financial advice.")
            return
        if not coin.isalnum() or len(coin) > 10:
            await message.reply_text("Please enter a valid coin symbol (letters/numbers, max 10 chars).\n\nCryptiq does not offer financial advice.")
            return
        user_id = str(user.id)
        alerts = database.load_alerts()
        if user_id not in alerts:
            alerts[user_id] = []
        alerts[user_id].append({"coin": coin, "price": price})
        database.save_alerts(alerts)
        await message.reply_text(f"Alert set for {coin.upper()} at ${price:,.2f}.\n\nCryptiq does not offer financial advice.")
    except Exception as e:
        utils.log_error(e, context="set_alert")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

async def delete_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    delete_profile handler. Removes the user's profile and all associated data, with confirmation and error handling.
    """
    try:
        user = getattr(update, 'effective_user', None)
        message = getattr(update, 'message', None)
        if user is None or message is None:
            return
        user_id = user.id
        try:
            data = database.load_user_data(user_id)
            if data:
                # Remove user from user_data.json
                all_data = {}
                try:
                    with open(database.USER_DATA_FILE, "r") as f:
                        all_data = json.load(f)
                except Exception:
                    pass
                if str(user_id) in all_data.get("users", {}):
                    del all_data["users"][str(user_id)]
                    with open(database.USER_DATA_FILE, "w") as f2:
                        json.dump(all_data, f2, indent=2)
                    await message.reply_text("Your profile and portfolio have been deleted.\n\nCryptiq does not offer financial advice.")
                else:
                    await message.reply_text("No profile found to delete.\n\nCryptiq does not offer financial advice.")
            else:
                await message.reply_text("No profile found to delete.\n\nCryptiq does not offer financial advice.")
        except Exception:
            await message.reply_text("Error deleting profile.\n\nCryptiq does not offer financial advice.")
    except Exception as e:
        utils.log_error(e, context="delete_profile")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- Settings, language, and menu handlers ---
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /settings command handler. Shows the user current settings and options to change them.
    """
    return await utils.settings_command(update, context)

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /language command handler. Displays available languages and current language setting.
    """
    return await utils.language_command(update, context)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /menu command handler. Shows the main menu with available actions for the user.
    """
    return await utils.main_menu(update, context)

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    set_language handler. Updates the user's language preference.
    """
    return await utils.set_language(update, context)

async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    language_chosen handler. Confirms and applies the user's language choice.
    """
    return await utils.language_chosen(update, context)

# --- News, alerts, and profile handlers ---
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    news handler. Sends the latest crypto news to the user, with error handling.
    """
    try:
        message = getattr(update, 'message', None)
        if message is None:
            return
        NEWS_API = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        try:
            resp = utils.requests.get(NEWS_API)
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
        utils.log_error(e, context="news")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

async def set_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    set_alert handler. Creates or updates a price alert for a specific cryptocurrency with input validation.
    """
    try:
        user = getattr(update, 'effective_user', None)
        message = getattr(update, 'message', None)
        args = getattr(context, 'args', None)
        if user is None or message is None or not args or len(args) < 2:
            if message is not None:
                await message.reply_text("Usage: /setalert <coin> <price>\nExample: /setalert btc 70000\n\nCryptiq does not offer financial advice.")
            return
        coin = args[0].lower()
        try:
            price = float(args[1])
            if price < 0 or price > 1e7:
                await message.reply_text("Please enter a valid, positive price (less than 10 million).\n\nCryptiq does not offer financial advice.")
                return
        except Exception:
            await message.reply_text("Usage: /setalert <coin> <price> (price must be a number)\n\nCryptiq does not offer financial advice.")
            return
        if not coin.isalnum() or len(coin) > 10:
            await message.reply_text("Please enter a valid coin symbol (letters/numbers, max 10 chars).\n\nCryptiq does not offer financial advice.")
            return
        user_id = str(user.id)
        alerts = database.load_alerts()
        if user_id not in alerts:
            alerts[user_id] = []
        alerts[user_id].append({"coin": coin, "price": price})
        database.save_alerts(alerts)
        await message.reply_text(f"Alert set for {coin.upper()} at ${price:,.2f}.\n\nCryptiq does not offer financial advice.")
    except Exception as e:
        utils.log_error(e, context="set_alert")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

async def delete_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    delete_profile handler. Removes the user's profile and all associated data, with confirmation and error handling.
    """
    try:
        user = getattr(update, 'effective_user', None)
        message = getattr(update, 'message', None)
        if user is None or message is None:
            return
        user_id = user.id
        try:
            data = database.load_user_data(user_id)
            if data:
                # Remove user from user_data.json
                all_data = {}
                try:
                    with open(database.USER_DATA_FILE, "r") as f:
                        all_data = json.load(f)
                except Exception:
                    pass
                if str(user_id) in all_data.get("users", {}):
                    del all_data["users"][str(user_id)]
                    with open(database.USER_DATA_FILE, "w") as f2:
                        json.dump(all_data, f2, indent=2)
                    await message.reply_text("Your profile and portfolio have been deleted.\n\nCryptiq does not offer financial advice.")
                else:
                    await message.reply_text("No profile found to delete.\n\nCryptiq does not offer financial advice.")
            else:
                await message.reply_text("No profile found to delete.\n\nCryptiq does not offer financial advice.")
        except Exception:
            await message.reply_text("Error deleting profile.\n\nCryptiq does not offer financial advice.")
    except Exception as e:
        utils.log_error(e, context="delete_profile")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- Button and message handlers ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    button_handler handler. Handles button presses in messages, such as inline keyboards.
    """
    return await utils.button_handler(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    handle_message handler. Processes incoming messages and responds appropriately, with input validation and error handling.
    """
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
        if not user_message or len(user_message) > 1000:
            await message.reply_text("Please enter a valid message (1-1000 characters).\n\nCryptiq does not offer financial advice.")
            return
        # ...existing code for chat logic...
        await utils.handle_message(update, context)
    except Exception as e:
        utils.log_error(e, context="handle_message")
        message = getattr(update, 'message', None)
        if message is not None:
            await message.reply_text("An error occurred. Please try again later. (Logged)")

# --- Help and onboarding handlers ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /help command handler. Provides information about available commands and bot usage.
    """
    return await utils.help_command(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start command handler. Begins onboarding or shows main menu for existing users.
    """
    return await utils.start(update, context)

async def ask_initial_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ask_initial_questions handler. Asks the user questions to set up their profile and preferences.
    """
    return await utils.ask_initial_questions(update, context)

async def handle_setup_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    handle_setup_answers handler. Processes answers to the initial setup questions.
    """
    return await utils.handle_setup_answers(update, context)

# --- Alert checker (background job) ---
async def alert_checker(app):
    """
    alert_checker job. Periodically checks and sends alerts for price thresholds.
    """
    return await utils.alert_checker(app)
