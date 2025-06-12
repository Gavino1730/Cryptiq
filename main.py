"""
Main entry point for Cryptiq Telegram bot.
Sets up the bot, registers handlers, and starts polling.
"""
import os
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, JobQueue
from dotenv import load_dotenv
import handlers

# Load environment variables from .env file for secrets and configuration
load_dotenv()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN must be set as an environment variable.")

# Initialize the Telegram bot application and job queue for background tasks
job_queue = JobQueue()
app = Application.builder().token(TELEGRAM_TOKEN).job_queue(job_queue).build()

# Register all command handlers for user commands (e.g., /start, /help, /portfolio, etc.)
app.add_handler(CommandHandler("start", handlers.start))           # Onboarding and main menu
app.add_handler(CommandHandler("help", handlers.help_command))     # Show help and command list
app.add_handler(CommandHandler("portfolio", handlers.show_portfolio)) # Show user's portfolio
app.add_handler(CommandHandler("setbank", handlers.set_bank))      # Set user's bank balance
app.add_handler(CommandHandler("setholdings", handlers.set_holdings)) # Set user's crypto holdings
app.add_handler(CommandHandler("setstrategy", handlers.set_strategy)) # Set user's trading strategy
app.add_handler(CommandHandler("setalert", handlers.set_alert))    # Set price alerts
app.add_handler(CommandHandler("news", handlers.news))             # Show latest crypto news
app.add_handler(CommandHandler("deleteprofile", handlers.delete_profile)) # Delete user profile and data
app.add_handler(CommandHandler("menu", handlers.main_menu))        # Show main menu with buttons
app.add_handler(CommandHandler("settings", handlers.settings_command)) # Show and change user settings
app.add_handler(CommandHandler("language", handlers.language_command)) # Change language

# Register message handler for all non-command text messages (AI chat, onboarding, etc.)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
# Register callback query handler for inline keyboard button presses
app.add_handler(CallbackQueryHandler(handlers.button_handler))

# Background job: check for triggered price alerts every 60 seconds
async def alert_checker_job(context):
    await handlers.alert_checker(app)
job_queue.run_repeating(alert_checker_job, interval=60, first=0)

if __name__ == "__main__":
    print("Cryptiq bot is running...")
    app.run_polling()  # Start polling for Telegram updates
