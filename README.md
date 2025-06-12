# Cryptiq – AI Crypto Portfolio Telegram Bot
<<<<<<< HEAD

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![Telegram](https://img.shields.io/badge/telegram-bot-blue.svg?logo=telegram)](https://t.me/yourbotusername)

=======
(I was lazy so a lot of the documentation was written with AI)
>>>>>>> 46501b3996c33302fddcd33840c86067345a3cb2
---

## 🚧 EARLY DEVELOPMENT NOTICE

**Cryptiq is in its earliest, pre-release form. This bot is experimental and under active development. There WILL be bugs, missing features, and unexpected behavior. Use at your own risk.**

---

## ⚠️ LEGAL DISCLAIMER

**Cryptiq does NOT provide financial, investment, or trading advice. All information and analysis provided by this bot is for informational and educational purposes only. You are solely responsible for your investment decisions. The developers and maintainers of Cryptiq are NOT liable for any losses, damages, or consequences resulting from the use of this bot.**

---

## What is Cryptiq?

Cryptiq is a Telegram bot that helps you track your crypto portfolio, get real-time prices, set price alerts, and more—all from inside Telegram. It uses AI to provide insights and supports multiple languages.

---

## Features

- Track your crypto portfolio and bank balance
- Get real-time prices and news
- Set price alerts
- AI-powered market analysis (experimental)
- Multi-language support
- Privacy-focused: your data is private

---

## Getting Started

### 1. **Clone the Repository**

If you don’t have git, [download it here](https://git-scm.com/downloads).

Open a terminal (Command Prompt, PowerShell, or Terminal) and run:
```sh
git clone https://github.com/yourusername/cryptiq.git
cd cryptiq
```

### 2. **Install Python**

Make sure you have Python 3.8 or newer.  
[Download Python here](https://www.python.org/downloads/).

Check your Python version:
```sh
python --version
```
or
```sh
python3 --version
```

### 3. **Install Required Libraries**

Install the required Python packages:
```sh
pip install -r requirements.txt
```
If you get an error, try:
```sh
python -m pip install -r requirements.txt
```

### 4. **Set Up Environment Variables**

1. Copy the example environment file:
   ```sh
   copy .env.example .env
   ```
   (On Mac/Linux: `cp .env.example .env`)

2. Open `.env` in a text editor and add your own API keys:
   - `TELEGRAM_TOKEN` – Get this from [BotFather](https://t.me/botfather) on Telegram.
   - `OPENAI_API_KEY` – Get this from [OpenAI](https://platform.openai.com/account/api-keys).

   Example `.env`:
   ```
   TELEGRAM_TOKEN=your-telegram-bot-token-here
   OPENAI_API_KEY=your-openai-api-key-here
   ```

### 5. **Run the Bot**

Start the bot with:
```sh
python cryptiq_bot.py
```
or
```sh
python3 cryptiq_bot.py
```

You should see a message that the bot is running.

---

## Using the Bot

1. **Find your bot on Telegram** (search for the name you set up with BotFather).
2. **Start a chat** and type `/start`.
3. Use `/menu` to see the main menu with buttons.
4. Use `/help` to see all commands.

---

## Common Commands

| Command            | Description                                 |
|--------------------|---------------------------------------------|
| /start             | Start or reset your profile                 |
| /portfolio         | Show your portfolio                         |
| /setbank           | Set your bank balance                       |
| /setholdings       | Set holdings for a coin                     |
| /setstrategy       | Set your trading strategy                   |
| /setalert          | Set a price alert                           |
| /news              | Show latest crypto news                     |
| /deleteprofile     | Delete your profile and data                |
| /menu              | Show the main menu                          |
| /settings          | Show and change settings                    |
| /language          | Change your language                        |
| /help              | Show help                                   |

---

## Troubleshooting

- **Bot won’t start?**  
  - Double-check your Python version and that you installed all requirements.
  - Make sure your `.env` file is filled out correctly.
- **Bot not responding in Telegram?**  
  - Make sure the bot is running in your terminal.
  - Check for errors in the terminal window.
- **Still stuck?**  
  - Open an issue on GitHub or contact the developer.

---

## Contributing

Pull requests and suggestions are welcome!  
Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes.

---

## Documentation

- [PRIVACY_POLICY.md](PRIVACY_POLICY.md) – How your data is handled
- [LICENSE](LICENSE) – MIT License

---

## Security & Privacy

- API keys are stored in `.env` (never share this file).
- User data is stored locally and not shared.
- You can delete your data at any time with `/deleteprofile`.

---

## For Developers

- Code is organized into logical modules for easier debugging.
- All secrets are loaded from environment variables.
- Logging is enabled for error tracking.
- See [CHANGELOG.md](CHANGELOG.md) for updates.

---

## Future Plans

Cryptiq is under active development! Here’s what we’re planning for the future:

- **Automated Trading:**  
  Integrate with crypto exchanges so users can execute trades directly from the bot (with full user control and security).

- **Predictions:**  
  Use AI and statistical models to provide experimental price predictions and trend analysis (with clear disclaimers).

- **Signals & Calls:**  
  Offer automated or community-driven trade signals, alerts, and market calls.

- **Portfolio Analytics:**  
  More advanced analytics, including profit/loss tracking, historical performance, and risk metrics.

- **Multi-Exchange Support:**  
  Connect and track balances across multiple exchanges and wallets.

- **DeFi & NFT Tracking:**  
  Support for DeFi positions and NFT holdings.

- **Customizable Alerts:**  
  More flexible alerting (e.g., by percentage change, volume, or news events).

- **Better Charting:**  
  Interactive and more detailed charts for portfolio and market data.

- **Community Features:**  
  Leaderboards, sharing, and group portfolio competitions.

- **Web, Desktop, and Mobile Apps:**  
  Cryptiq will eventually become available as a full-featured web app, desktop software, and mobile app for iOS and Android, making it even easier to manage your crypto portfolio anywhere.

---

**Have a feature request or idea?**  
Open an issue or discussion on GitHub!

---

## Disclaimer

Cryptiq does **not** offer financial advice. All information is for educational purposes only.

---

## Need Help?

If you have any questions, open an issue on GitHub or contact the developer.

---

**Enjoy using Cryptiq!**
