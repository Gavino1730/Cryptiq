"""
Main entry point for Cryptiq Telegram bot.
Sets up the bot, registers handlers, and starts polling.
"""
import os
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, JobQueue
from dotenv import load_dotenv
import handlers

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN must be set as an environment variable.")

# Set up the bot application
job_queue = JobQueue()
app = Application.builder().token(TELEGRAM_TOKEN).job_queue(job_queue).build()

# Register command handlers
app.add_handler(CommandHandler("start", handlers.start))
app.add_handler(CommandHandler("help", handlers.help_command))
app.add_handler(CommandHandler("portfolio", handlers.show_portfolio))
app.add_handler(CommandHandler("setbank", handlers.set_bank))
app.add_handler(CommandHandler("setholdings", handlers.set_holdings))
app.add_handler(CommandHandler("setstrategy", handlers.set_strategy))
app.add_handler(CommandHandler("setalert", handlers.set_alert))
app.add_handler(CommandHandler("news", handlers.news))
app.add_handler(CommandHandler("deleteprofile", handlers.delete_profile))
app.add_handler(CommandHandler("menu", handlers.main_menu))
app.add_handler(CommandHandler("settings", handlers.settings_command))
app.add_handler(CommandHandler("language", handlers.language_command))

# Register message and callback handlers
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
app.add_handler(CallbackQueryHandler(handlers.button_handler))

# Start alert checker in background
async def alert_checker_job(context):
    await handlers.alert_checker(app)
job_queue.run_repeating(alert_checker_job, interval=60, first=0)

if __name__ == "__main__":
    print("Cryptiq bot is running...")
    app.run_polling()
