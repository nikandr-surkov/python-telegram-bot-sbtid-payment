# Python Telegram Bot with SBTID Payment

A Python-based Telegram bot for processing and verifying Social Bound Identity Tokens (SBTID) on the TON blockchain. This project demonstrates how to create a blockchain-powered payment system that securely binds users' Telegram IDs to their NFT purchases without requiring a database.

## What is Social Bound Identity Token (SBTID)?

SBTID is a new type of Social Bound Token developed by Nikandr Surkov. The main feature of such token is each token contains social ID information of user that should get access to digital product inside the selected social network. You can easily use it with any social network where you can get the user id information. 

The main field right now is using it on Telegram. You can think of SBTID as tickets in real life but instead of names on the tickets we have Telegram user ID with SBTID. It's very easy to verify if user has minted the token with provided id (made a payment).

Payments are transferred to SBTID collection creators during each mint transaction. So, after each payment the creator wallet is increasing by the amount user paid (except blockchain fees) automatically.

### How does it work?
1. Deploy SBTID token collection https://sbtid.nikandr.com/deploy
2. Provide user with the following payment link: https://sbtid.nikandr.com/collection?contract={CONTRACT_ADDRESS}&socialId={USER_ID}
3. Verify user made the payment. Just call get function get_nft_address_by_index to your token contract providing user id, it will return predetermined smart contract address of NFT token with desired id. Check if this address is active. If it is active address, user made the successful payment.

## Project Overview

This bot enables:
- Seamless integration between Telegram and TON blockchain
- Web app-based payment processing for NFT purchases
- On-chain verification of token ownership
- User-friendly payment and verification experience

## Bot Features

- `/start` - Welcome message with payment options
- Payment verification via callback buttons
- Secure Web App integration
- Real-time NFT status checking
- TON blockchain integration

## Prerequisites

- Python 3.7 or higher
- aiogram library
- python-dotenv library
- pytoniq-core library
- aiohttp library
- A Telegram Bot Token (from @BotFather)
- A TON smart contract address for your SBTID collection
- TON QuickNode API access

## Getting Started

### Option 1: Using PyCharm

1. Open PyCharm
2. Go to `File > Project from Version Control`
3. Enter URL: `https://github.com/nikandr-surkov/python-telegram-bot-sbtid-payment.git`
4. Choose your project directory
5. Click "Clone"
6. Install dependencies:
   ```bash
   pip install aiogram python-dotenv pytoniq-core aiohttp
   ```

### Option 2: Using Terminal

1. Clone the repository:
   ```bash
   git clone https://github.com/nikandr-surkov/python-telegram-bot-sbtid-payment.git
   cd python-telegram-bot-sbtid-payment
   ```
2. Install dependencies:
   ```bash
   pip install aiogram python-dotenv pytoniq-core aiohttp
   ```
3. Create a `.env` file:
   ```
   BOT_TOKEN=your_bot_token_here
   CONTRACT_ADDRESS=your_contract_address_here
   QUICKNODE_ENDPOINT=your_quicknode_endpoint_here
   ```
4. Run the bot:
   ```bash
   python main.py
   ```

## Project Structure

- `main.py`: Main bot script with all handlers and logic
- `.env`: Environment variables (not included in repo)
- `.env.example`: Example environment variables
- `README.md`: Project documentation

## Key Features

- Dynamic payment link generation based on user ID
- Asynchronous TON blockchain interaction
- Smart contract data parsing
- Secure WebApp validation
- Efficient resource management with session reuse
- Comprehensive error handling and logging

## Technologies Used

- Python 3
- aiogram (Telegram Bot API framework)
- TON Blockchain
- pytoniq-core (TON address parsing)
- QuickNode API (TON blockchain interaction)
- Telegram Web Apps

## Bot Configuration

1. Create a new bot with @BotFather
2. Enable inline mode if needed
3. Set up commands using /setcommands:
   ```
   start - Start the bot and see payment options
   ```

## Web App Integration

The bot includes integration with SBTID Web App for payment processing. To set up:

1. Deploy your SBTID collection at https://sbtid.nikandr.com/deploy
2. Copy your contract address to `.env` file
3. Test the integration

## Blockchain Interaction

The bot interacts with the TON blockchain to:
- Verify if a user has minted an NFT
- Parse blockchain data using pytoniq-core

## Error Handling

The bot includes comprehensive error handling:
- Blockchain API errors
- Web App data validation
- Smart contract error codes
- Network and connection handling
- Logging for debugging

## Learn More

- [TON Blockchain Documentation](https://docs.ton.org/)
- [SBTID Platform](https://sbtid.nikandr.com/)
- [TON SBT Standard](https://github.com/ton-blockchain/TEPs/blob/master/text/0085-sbt-standard.md)
- [aiogram Documentation](https://docs.aiogram.dev/)

## Author
### Nikandr Surkov
- 🌐 Website: https://nikandr.com
- 📺 YouTube: https://www.youtube.com/@NikandrSurkov
- 📱 Telegram: https://t.me/nikandr_s
- 📢 Telegram Channel: https://t.me/+hL2jdmRkhf9jZjQy
- 📰 Clicker Game News: https://t.me/clicker_game_news
- 💻 GitHub: https://github.com/nikandr-surkov
- 🐦 Twitter: https://x.com/NikandrSurkov
- 💼 LinkedIn: https://www.linkedin.com/in/nikandr-surkov/
- ✍️ Medium: https://medium.com/@NikandrSurkov