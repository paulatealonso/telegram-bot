from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
import os
from dotenv import load_dotenv
from mnemonic import Mnemonic
from tonsdk.crypto import mnemonic_to_wallet_key
from tonsdk.utils import to_nano

# Load environment variables
load_dotenv()
TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
TON_API_KEY = os.getenv('TON_API_KEY')
TON_WALLET_ADDRESS = os.getenv('TON_WALLET_ADDRESS')
TON_PRIVATE_KEY = os.getenv('TON_PRIVATE_KEY')
TONCENTER_API_URL = os.getenv('TONCENTER_API_URL')

# Function to generate a new TON wallet
async def generate_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Generate a new mnemonic phrase
        mnemo = Mnemonic("english")
        mnemonic = mnemo.generate(strength=256)
        
        # Convert mnemonic phrase to private and public keys
        wallet_keys = mnemonic_to_wallet_key(mnemonic)
        private_key, public_key = wallet_keys

        # Manually create the wallet address
        wallet_address = f"EQ{public_key.hex()[:48]}"

        # Prepare the response message
        response_message = (
            f"🎉 **New Wallet Generated!** 🎉\n\n"
            f"🔑 **Address:** `{wallet_address}`\n\n"
            f"📝 **Seed Phrase:** `{mnemonic}`\n\n"
            f"⚠️ **Important Security Notice:**\n"
            f"1️⃣ **Write down your seed phrase on paper.** Do not save it digitally.\n"
            f"2️⃣ **Never share your seed phrase with anyone.** It grants full access to your wallet.\n"
            f"3️⃣ **Store your seed phrase in a safe place.** If you lose it, you cannot recover your wallet.\n"
            f"4️⃣ **After saving your seed phrase, delete this message.** For your safety, the bot will not display this information again.\n\n"
            f"🔒 **Your wallet has been successfully created.** You can now use this address to receive TON coins."
        )

        await update.message.reply_text(response_message, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f'Error: {str(e)}')
        print(f'Error: {str(e)}')

# Start function
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await generate_wallet(update, context)

# Help function
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Available commands:\n"
        "/start - Start the bot and generate a new wallet\n"
        "/help - Show this help message\n"
        "/buy <amount> <destination_wallet> - Buy TON coins\n"
        "/sell <amount> <source_wallet> - Sell TON coins\n"
        "/generatewallet - Generate a new TON wallet with 24 words of security\n"
    )
    await update.message.reply_text(help_text)

# Function to buy TON coins
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text('Usage: /buy <amount> <destination_wallet>')
        return

    try:
        amount = float(context.args[0])
        user_wallet = context.args[1]
        fee = amount * 0.03  # 3% fee
        amount_after_fee = amount - fee

        headers = {
            'Authorization': f'Bearer {TON_API_KEY}',
            'Content-Type': 'application/json'
        }

        # Send the amount after deducting the fee to the user
        response = requests.post(TONCENTER_API_URL + "/sendTransaction", headers=headers, json={
            "from": TON_WALLET_ADDRESS,
            "to": user_wallet,
            "value": to_nano(amount_after_fee, "ton"),
            "private_key": TON_PRIVATE_KEY
        })

        if response.status_code == 200:
            await update.message.reply_text(f'Transaction successful: {response.json()}')
        else:
            await update.message.reply_text(f'Error: {response.json()}')

    except Exception as e:
        await update.message.reply_text(f'Error: {str(e)}')
        print(f'Error: {str(e)}')

# Function to sell TON coins
async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text('Usage: /sell <amount> <source_wallet>')
        return

    try:
        amount = float(context.args[0])
        user_wallet = context.args[1]
        fee = amount * 0.03  # 3% fee
        amount_after_fee = amount - fee

        headers = {
            'Authorization': f'Bearer {TON_API_KEY}',
            'Content-Type': 'application/json'
        }

        # Receive the amount from the user to your wallet
        response = requests.post(TONCENTER_API_URL + "/receiveTransaction", headers=headers, json={
            "from": user_wallet,
            "to": TON_WALLET_ADDRESS,
            "value": to_nano(amount_after_fee, "ton"),
            "private_key": TON_PRIVATE_KEY
        })

        if response.status_code == 200:
            await update.message.reply_text(f'Transaction successful: {response.json()}')
        else:
            await update.message.reply_text(f'Error: {response.json()}')

    except Exception as e:
        await update.message.reply_text(f'Error: {str(e)}')
        print(f'Error: {str(e)}')

def main() -> None:
    application = Application.builder().token(TELEGRAM_API_KEY).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('buy', buy))
    application.add_handler(CommandHandler('sell', sell))
    application.add_handler(CommandHandler('generatewallet', generate_wallet))

    application.run_polling()

if __name__ == '__main__':
    main()
