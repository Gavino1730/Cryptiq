"""
Telegram command and message handlers for Cryptiq bot.
"""
from telegram import Update, ForceReply
from telegram.ext import ContextTypes
import database
import utils
import keyboards

# --- Handler functions ---
# All handler functions from cryptiq_bot.py are moved here.
# Imports from utils/database/keyboards are used for data and helpers.

# --- Portfolio and analytics handlers ---
async def show_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ...moved from cryptiq_bot.py...
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
            import json
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
    return await utils.settings_command(update, context)

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.language_command(update, context)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.main_menu(update, context)

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.set_language(update, context)

async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.language_chosen(update, context)

# --- News, alerts, and profile handlers ---
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.news(update, context)

async def set_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.set_alert(update, context)

async def delete_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.delete_profile(update, context)

# --- Bank and holdings handlers ---
async def setbank_natural(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.setbank_natural(update, context)

async def setholdings_natural(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.setholdings_natural(update, context)

async def set_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.set_bank(update, context)

async def set_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.set_strategy(update, context)

async def set_holdings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.set_holdings(update, context)

# --- Button and message handlers ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.button_handler(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.handle_message(update, context)

# --- Help and onboarding handlers ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.help_command(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.start(update, context)

async def ask_initial_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.ask_initial_questions(update, context)

async def handle_setup_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await utils.handle_setup_answers(update, context)

# --- Alert checker (background job) ---
async def alert_checker(app):
    return await utils.alert_checker(app)
