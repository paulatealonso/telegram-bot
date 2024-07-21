from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
import os
from dotenv import load_dotenv
from mnemonic import Mnemonic

# Cargar variables de entorno
load_dotenv()
TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
TON_API_KEY = os.getenv('TON_API_KEY')
TON_WALLET_ADDRESS = os.getenv('TON_WALLET_ADDRESS')
TON_PRIVATE_KEY = os.getenv('TON_PRIVATE_KEY')
TONCENTER_API_URL = os.getenv('TONCENTER_API_URL')

# Función de inicio
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hello! I am a bot for TON transactions. Use /buy to buy coins, /sell to sell coins, /generatewallet to generate a new wallet, and /help to see the available commands.')

# Función de ayuda
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/buy <amount> <destination_wallet> - Buy TON coins\n"
        "/sell <amount> <source_wallet> - Sell TON coins\n"
        "/generatewallet - Generate a new TON wallet with 24 words of security\n"
    )
    await update.message.reply_text(help_text)

# Función para generar una nueva billetera TON
async def generate_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Generar una nueva frase mnemónica
        mnemo = Mnemonic("english")
        mnemonic = mnemo.generate(strength=256)
        seed = mnemo.to_seed(mnemonic)

        # Simulación de generación de dirección de billetera (esto necesitaría ser reemplazado por una lógica real)
        wallet_address = "Generated_Wallet_Address"

        response_message = f"Your new TON wallet has been generated!\nAddress: {wallet_address}\nSeed Phrase: {mnemonic}"
        await update.message.reply_text(response_message)
    except Exception as e:
        await update.message.reply_text(f'Error: {str(e)}')
        print(f'Error: {str(e)}')

# Función para comprar monedas TON
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

        # Enviar la cantidad después de deducir la tarifa al usuario
        response = requests.post(TONCENTER_API_URL + "/sendTransaction", headers=headers, json={
            "from": TON_WALLET_ADDRESS,
            "to": user_wallet,
            "value": amount_after_fee,
            "private_key": TON_PRIVATE_KEY
        })

        if response.status_code == 200:
            await update.message.reply_text(f'Transaction successful: {response.json()}')
        else:
            await update.message.reply_text(f'Error: {response.json()}')

    except Exception as e:
        await update.message.reply_text(f'Error: {str(e)}')
        print(f'Error: {str(e)}')

# Función para vender monedas TON
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

        # Recibir la cantidad desde el usuario a tu billetera
        response = requests.post(TONCENTER_API_URL + "/receiveTransaction", headers=headers, json={
            "from": user_wallet,
            "to": TON_WALLET_ADDRESS,
            "value": amount_after_fee,
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
