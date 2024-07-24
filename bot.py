from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
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

# In-memory storage for user wallets
user_wallets = {}

# Function to generate a new TON wallet
def generate_wallet():
    mnemo = Mnemonic("english")
    mnemonic = mnemo.generate(strength=256)
    wallet_keys = mnemonic_to_wallet_key(mnemonic)
    private_key, public_key = wallet_keys
    wallet_address = f"EQ{public_key.hex()[:48]}"
    return wallet_address, mnemonic

# Function to get the welcome message
def get_welcome_message() -> str:
    return (
        "🎉 **Welcome to TON Call Secure Bot!** 🎉\n\n"
        "🔒 This bot helps you manage your TON wallets securely.\n"
        "💼 You can generate, view, and connect wallets, and perform transactions.\n\n"
        "🌐 [TON Call Secure Bot](https://web.telegram.org/k/#@HigherTonBot)\n\n"
        "Please choose an option to get started:"
    )

# Start function
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = get_welcome_message()

    keyboard = [
        [InlineKeyboardButton("➕ Generate Wallet", callback_data='newwallet')],
        [InlineKeyboardButton("🔍 View Wallets", callback_data='viewwallets')],
        [InlineKeyboardButton("🔗 Connect Wallet", callback_data='connectwallet')],
        [InlineKeyboardButton("ℹ️ Help", callback_data='help')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

# Home function
async def home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id in user_wallets and user_wallets[user_id]:
        await send_main_menu(update.message, True)
    else:
        await send_main_menu(update.message, False)

# Main menu function
async def send_main_menu(message, has_wallet: bool) -> None:
    welcome_message = get_welcome_message()
    if has_wallet:
        keyboard = [
            [InlineKeyboardButton("📜 Wallets", callback_data='wallets')],
            [InlineKeyboardButton("💰 Buy TON", callback_data='buy')],
            [InlineKeyboardButton("💸 Sell TON", callback_data='sell')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("➕ Generate Wallet", callback_data='newwallet')],
            [InlineKeyboardButton("🔗 Connect Wallet", callback_data='connectwallet')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')],
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

# Callback handler for button presses
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    command = query.data

    if command == 'wallets':
        await wallets_menu(update, context)
    elif command == 'connectwallet':
        await connect_wallet(update, context)
    elif command == 'buy':
        await query.edit_message_text("Use the command /buy <amount> <destination_wallet> to buy TON coins.")
    elif command == 'sell':
        await query.edit_message_text("Use the command /sell <amount> <source_wallet> to sell TON coins.")
    elif command == 'help':
        await help_command(update, context)
    elif command == 'viewwallets':
        await view_wallets(update, context)
    elif command.startswith('viewwallet_'):
        await view_wallet(update, context, command.split('_')[1])
    elif command == 'newwallet':
        await generate_and_store_wallet(update, context)
    elif command.startswith('viewlastwallet_'):
        await view_wallet(update, context, command.split('_')[1])
    elif command == 'mainmenu':
        user_id = update.callback_query.from_user.id
        if user_id in user_wallets and user_wallets[user_id]:
            await send_main_menu(query.message, True)
        else:
            await send_main_menu(query.message, False)
    elif command.startswith('managewallet_'):
        await manage_wallet(update, context, command.split('_')[1])
    elif command.startswith('deletewallet_'):
        await delete_wallet(update, context, command.split('_')[1])

# Function to display wallets menu
async def wallets_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("➕ New Wallet", callback_data='newwallet')],
        [InlineKeyboardButton("🔗 Connect Wallet", callback_data='connectwallet')],
        [InlineKeyboardButton("🔍 View Wallets", callback_data='viewwallets')],
        [InlineKeyboardButton("⬅️ Back", callback_data='mainmenu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text('Wallet Management:', reply_markup=reply_markup)

# Function to generate and store a new wallet
async def generate_and_store_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.callback_query.from_user.id
    wallet_address, mnemonic = generate_wallet()

    # Store the wallet in the user's list
    if user_id not in user_wallets:
        user_wallets[user_id] = []
    user_wallets[user_id].append({
        "address": wallet_address,
        "mnemonic": mnemonic
    })

    # Get the index of the newly created wallet
    wallet_index = len(user_wallets[user_id]) - 1

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

    keyboard = [
        [InlineKeyboardButton("⬅️ Back", callback_data=f'viewwallet_{wallet_index}')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(response_message, parse_mode='Markdown', reply_markup=reply_markup)

# Function to display user's wallets
async def view_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.callback_query.from_user.id
    if user_id in user_wallets and user_wallets[user_id]:
        wallets = user_wallets[user_id]
        keyboard = [
            [InlineKeyboardButton(f"Wallet {i+1}", callback_data=f'viewwallet_{i}')] for i in range(len(wallets))
        ]
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='mainmenu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text('Your Wallets:', reply_markup=reply_markup)
    else:
        keyboard = [
            [InlineKeyboardButton("➕ Generate Wallet", callback_data='newwallet')],
            [InlineKeyboardButton("🔗 Connect Wallet", callback_data='connectwallet')],
            [InlineKeyboardButton("⬅️ Back", callback_data='mainmenu')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text("You don't have any wallets yet. Use the options to create or connect a wallet.", reply_markup=reply_markup)

# Function to view a specific wallet
async def view_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_index: str) -> None:
    user_id = update.callback_query.from_user.id
    wallet_index = int(wallet_index)
    if user_id in user_wallets and wallet_index < len(user_wallets[user_id]):
        wallet = user_wallets[user_id][wallet_index]
        await update.callback_query.edit_message_text(
            f"{get_welcome_message()}\n\n"
            f"🔑 **Wallet Address:** `{wallet['address']}`\n"
            f"💰 **Balance:** 0.0 TON (dummy value for now)\n"
            f"⬅️ **Options:**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 Sell TON", callback_data='sell')],
                [InlineKeyboardButton("⚙️ Manage Wallet", callback_data=f'managewallet_{wallet_index}')],
                [InlineKeyboardButton("🔄 Refresh", callback_data=f'viewwallet_{wallet_index}')],
                [InlineKeyboardButton("⬅️ Back", callback_data='mainmenu')]
            ]),
            parse_mode='Markdown'
        )
    else:
        await update.callback_query.edit_message_text("Invalid wallet index. Please select a valid wallet.")

# Function to manage a specific wallet
async def manage_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_index: str) -> None:
    user_id = update.callback_query.from_user.id
    wallet_index = int(wallet_index)
    if user_id in user_wallets and wallet_index < len(user_wallets[user_id]):
        wallet = user_wallets[user_id][wallet_index]
        keyboard = [
            [InlineKeyboardButton("❌ Delete Wallet", callback_data=f'deletewallet_{wallet_index}')],
            [InlineKeyboardButton("⬅️ Back", callback_data=f'viewwallet_{wallet_index}')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            f"{get_welcome_message()}\n\n"
            f"🔑 **Wallet Address:** `{wallet['address']}`\n"
            f"💰 **Balance:** 0.0 TON (dummy value for now)\n\n"
            f"🔧 **Manage Wallet Options:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# Function to delete a specific wallet
async def delete_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_index: str) -> None:
    user_id = update.callback_query.from_user.id
    wallet_index = int(wallet_index)
    if user_id in user_wallets and wallet_index < len(user_wallets[user_id]):
        del user_wallets[user_id][wallet_index]
        if not user_wallets[user_id]:
            del user_wallets[user_id]
        await view_wallets(update, context)

# Function to connect an existing wallet
async def connect_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.edit_message_text("Please send your wallet address and seed phrase in the following format:\n`/connect <wallet_address> <seed_phrase>`", parse_mode='Markdown')

# Function to handle the /connect command
async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    try:
        args = update.message.text.split(' ', 2)
        wallet_address = args[1]
        seed_phrase = args[2]
        if user_id not in user_wallets:
            user_wallets[user_id] = []
        user_wallets[user_id].append({
            "address": wallet_address,
            "mnemonic": seed_phrase
        })
        await update.message.reply_text(f"Wallet `{wallet_address}` connected successfully.", parse_mode='Markdown')
    except IndexError:
        await update.message.reply_text("Usage: /connect <wallet_address> <seed_phrase>")

# Help function
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/home - Access the main menu\n"
        "/connect <wallet_address> <seed_phrase> - Connect an existing wallet\n"
        "/buy <amount> <destination_wallet> - Buy TON coins\n"
        "/sell <amount> <source_wallet> - Sell TON coins\n"
        "/help - Show this help message\n"
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

def main() -> None:
    application = Application.builder().token(TELEGRAM_API_KEY).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('home', home))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('buy', buy))
    application.add_handler(CommandHandler('sell', sell))
    application.add_handler(CommandHandler('connect', connect))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
