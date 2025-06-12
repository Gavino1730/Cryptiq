# Cryptiq – AI Crypto Portfolio Telegram Bot

---

## 🚧 EARLY DEVELOPMENT NOTICE

**Cryptiq is in its earliest, pre-release form. This bot is experimental and under active development. There WILL be bugs, missing features, and unexpected behavior. Use at your own risk.**

---

## ⚠️ LEGAL DISCLAIMER

**Cryptiq does NOT provide financial, investment, or trading advice. All information and analysis provided by this bot is for informational and educational purposes only. You are solely responsible for your investment decisions. The developers and maintainers of Cryptiq are NOT liable for any losses, damages, or consequences resulting from the use of this bot.**

---

## Features

- Track your crypto portfolio
- Get real-time prices and news
- Set price alerts
- AI-powered market analysis (experimental)
- Multi-language support

---

## Setup

1. **Clone the repo:**
   ```sh
   git clone https://github.com/yourusername/cryptiq.git
   cd cryptiq
   ```

2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

3. **Set your API keys:**
   - Edit `cryptiq_bot.py` and set your `TELEGRAM_TOKEN` and `OPENAI_API_KEY`.
   - (Optional) Use environment variables for better security.

4. **Run the bot:**
   ```sh
   python cryptiq_bot.py
   ```

---

## Usage

- Start the bot on Telegram with `/start`.
- Use `/menu` to access the main menu with buttons.
- Use `/portfolio` to view your portfolio.
- Use `/setbank <amount>` and `/setholdings <coin> <amount>` to update your data.
- Use `/setalert <coin> <price>` to set price alerts.
- Use `/news` for the latest headlines.
- Use `/help` for a list of commands.

---

## Security & Privacy

- API keys are required for Telegram and OpenAI.
- User data is stored locally in JSON files by default.
- For production, consider using a secure database and environment variables.
- Never share your API keys publicly.

---

## Contributing

Pull requests and suggestions are welcome! Please open an issue first to discuss changes.

---

## License

MIT License

---

## Disclaimer

Cryptiq does **not** offer financial advice. All information is for educational purposes only.
