from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import requests
import os
from dotenv import load_dotenv
from mnemonic import Mnemonic
from tonsdk.crypto import mnemonic_to_wallet_key
from tonsdk.utils import to_nano
import random

# Load environment variables
load_dotenv()
TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
TON_API_KEY = os.getenv('TON_API_KEY')
TON_WALLET_ADDRESS = os.getenv('TON_WALLET_ADDRESS')
TON_PRIVATE_KEY = os.getenv('TON_PRIVATE_KEY')
TONCENTER_API_URL = os.getenv('TONCENTER_API_URL')

# In-memory storage for user wallets and languages
user_wallets = {}
user_languages = {}

# Function to generate a new TON wallet with mixed language mnemonics
def generate_wallet() -> tuple[str, str]:
    mnemo = Mnemonic("english")
    mnemonic_english = mnemo.generate(strength=256)
    mnemonic_spanish = Mnemonic("spanish").generate(strength=256)
    combined_mnemonic = random.sample(mnemonic_english.split(), 12) + random.sample(mnemonic_spanish.split(), 12)
    random.shuffle(combined_mnemonic)
    mnemonic = ' '.join(combined_mnemonic)
    wallet_keys = mnemonic_to_wallet_key(mnemonic)
    private_key, public_key = wallet_keys
    wallet_address = f"EQ{public_key.hex()[:48]}"
    return wallet_address, mnemonic

# Function to get the welcome message
def get_welcome_message(wallet_info=None, lang='en') -> str:
    welcome_message = {
        'en': (
            "🎉 **Welcome to TON Call Secure Bot!** 🎉\n\n"
            "🔒 This bot helps you manage your TON wallets securely.\n"
            "💼 You can generate, view, and connect wallets, and perform transactions.\n\n"
            "🌐 [TON Call Secure](https://t.me/TONCALLSECURE)\n\n"
            "Please choose an option to get started:"
        ),
        'es': (
            "🎉 **Bienvenido a TON Call Secure Bot!** 🎉\n\n"
            "🔒 Este bot te ayuda a gestionar tus billeteras TON de forma segura.\n"
            "💼 Puedes generar, ver y conectar billeteras, y realizar transacciones.\n\n"
            "🌐 [TON Call Secure](https://t.me/TONCALLSECURE)\n\n"
            "Por favor, elige una opción para comenzar:"
        ),
        'ru': (
            "🎉 **Добро пожаловать в TON Call Secure Bot!** 🎉\n\n"
            "🔒 Этот бот помогает вам безопасно управлять вашими кошельками TON.\n"
            "💼 Вы можете создавать, просматривать и подключать кошельки, а также выполнять транзакции.\n\n"
            "🌐 [TON Call Secure](https://t.me/TONCALLSECURE)\n\n"
            "Пожалуйста, выберите опцию для начала:"
        ),
        'fr': (
            "🎉 **Bienvenue sur TON Call Secure Bot!** 🎉\n\n"
            "🔒 Ce bot vous aide à gérer vos portefeuilles TON en toute sécurité.\n"
            "💼 Vous pouvez générer, visualiser et connecter des portefeuilles, et effectuer des transactions.\n\n"
            "🌐 [TON Call Secure](https://t.me/TONCALLSECURE)\n\n"
            "Veuillez choisir une option pour commencer :"
        ),
        'de': (
            "🎉 **Willkommen beim TON Call Secure Bot!** 🎉\n\n"
            "🔒 Dieser Bot hilft Ihnen, Ihre TON-Wallets sicher zu verwalten.\n"
            "💼 Sie können Wallets erstellen, anzeigen und verbinden sowie Transaktionen durchführen.\n\n"
            "🌐 [TON Call Secure](https://t.me/TONCALLSECURE)\n\n"
            "Bitte wählen Sie eine Option, um zu beginnen:"
        ),
        'pl': (
            "🎉 **Witamy w TON Call Secure Bot!** 🎉\n\n"
            "🔒 Ten bot pomaga bezpiecznie zarządzać portfelami TON.\n"
            "💼 Możesz generować, przeglądać i łączyć portfele oraz wykonywać transakcje.\n\n"
            "🌐 [TON Call Secure](https://t.me/TONCALLSECURE)\n\n"
            "Proszę wybrać opcję, aby rozpocząć:"
        )
    }
    message = welcome_message.get(lang, welcome_message['en'])
    if wallet_info:
        message += (
            f"\n\n🔑 **Your Wallet Address:** `{wallet_info['address']}`\n"
            f"💰 **Balance:** 0.0 TON (dummy value for now)\n"
        )
    return message

# Start function
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        user_id = update.message.from_user.id
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
    else:
        return

    lang = user_languages.get(user_id, 'en')

    if user_id in user_wallets and user_wallets[user_id]:
        wallet_info = user_wallets[user_id][-1]
        welcome_message = get_welcome_message(wallet_info, lang)
        keyboard = [
            [InlineKeyboardButton("💼 Sell and Manage 💼", callback_data=f'sell_manage_{len(user_wallets[user_id]) - 1}')],
            [InlineKeyboardButton("📜 Wallets", callback_data='wallets')],
            [InlineKeyboardButton("⚙️ Settings", callback_data='settings')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
        ]
    else:
        welcome_message = get_welcome_message(lang=lang)
        keyboard = [
            [InlineKeyboardButton("➕ Generate Wallet", callback_data='newwallet')],
            [InlineKeyboardButton("🔗 Connect Wallet", callback_data='connectwallet')],
            [InlineKeyboardButton("⚙️ Settings", callback_data='settings')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

# Home function
async def home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    await send_main_menu(update.message, user_id)

# Main menu function
async def send_main_menu(message, user_id: int) -> None:
    lang = user_languages.get(user_id, 'en')
    if user_id in user_wallets and user_wallets[user_id]:
        wallet_info = user_wallets[user_id][-1]
        welcome_message = get_welcome_message(wallet_info, lang)
        keyboard = [
            [InlineKeyboardButton("💼 Sell and Manage 💼", callback_data=f'sell_manage_{len(user_wallets[user_id]) - 1}')],
            [InlineKeyboardButton("📜 Wallets", callback_data='wallets')],
            [InlineKeyboardButton("⚙️ Settings", callback_data='settings')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
        ]
    else:
        welcome_message = get_welcome_message(lang=lang)
        keyboard = [
            [InlineKeyboardButton("➕ Generate Wallet", callback_data='newwallet')],
            [InlineKeyboardButton("🔗 Connect Wallet", callback_data='connectwallet')],
            [InlineKeyboardButton("⚙️ Settings", callback_data='settings')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')],
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

# Helper function to compare message contents
def message_content_changed(current_message, new_text, new_reply_markup):
    return current_message.text != new_text or current_message.reply_markup != new_reply_markup

# Callback handler for button presses
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    command = query.data

    if command == 'wallets':
        await wallets_menu(update, context)
    elif command == 'connectwallet':
        await connect_wallet(update, context)
    elif command.startswith('sell_manage_'):
        wallet_index = int(command.split('_')[-1])
        await sell_manage_menu(update, context, wallet_index)
    elif command.startswith('deposit_'):
        wallet_index = int(command.split('_')[-1])
        await deposit_ton(update, context, wallet_index)
    elif command.startswith('withdraw_all_'):
        wallet_index = int(command.split('_')[-1])
        await withdraw_all_ton(update, context, wallet_index)
    elif command.startswith('withdraw_x_'):
        wallet_index = int(command.split('_')[-1])
        await withdraw_x_ton(update, context, wallet_index)
    elif command.startswith('disconnect_'):
        wallet_index = int(command.split('_')[-1])
        await disconnect_wallet(update, context, wallet_index)
    elif command == 'help':
        await help_command(update, context)
    elif command == 'viewwallets':
        await view_wallets(update, context)
    elif command.startswith('viewwallet_'):
        await view_wallet(update, context, command.split('_')[1])
    elif command == 'newwallet':
        await generate_and_store_wallet(update, context)
    elif command == 'mainmenu':
        user_id = query.from_user.id
        await send_main_menu(query.message, user_id)
    elif command.startswith('deletewallet_'):
        await delete_wallet(update, context, command.split('_')[1])
    elif command == 'settings':
        await settings_menu(update, context)
    elif command == 'change_language':
        await change_language_menu(update, context)
    elif command.startswith('set_lang_'):
        await set_language(update, context, command.split('_')[2])
    elif command == 'deletewallet':
        await delete_wallet_menu(update, context)
    elif command.startswith('buy_'):
        await handle_buy_command(update, context, command)
    elif command.startswith('chart_'):
        wallet_address = command.split('_')[-1]
        await send_chart_link(update, context, wallet_address)
    elif command.startswith('refresh_'):
        wallet_address = command.split('_')[-1]
        await refresh_coin_info(update, context, wallet_address)
    elif command.startswith('cancel_'):
        await send_main_menu(update.callback_query.message, update.callback_query.from_user.id)

# Function to display sell and manage menu
async def sell_manage_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_index: int) -> None:
    user_id = update.callback_query.from_user.id
    lang = user_languages.get(user_id, 'en')
    wallet_info = user_wallets[user_id][wallet_index] if user_id in user_wallets and len(user_wallets[user_id]) > wallet_index else None
    welcome_message = get_welcome_message(wallet_info, lang)
    
    # Prepare positions text
    positions_text = "\n".join([f"{coin}: {amount} TON" for coin, amount in wallet_info["positions"].items()])
    if not positions_text:
        positions_text = "No positions added yet."

    full_message = (
        f"{welcome_message}\n\n"
        f"💼 **Your Positions:**\n{positions_text}\n\n"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("💸 Withdraw All TON", callback_data=f'withdraw_all_{wallet_index}'),
            InlineKeyboardButton("💸 Withdraw X TON", callback_data=f'withdraw_x_{wallet_index}')
        ],
        [
            InlineKeyboardButton("💸 Deposit TON", callback_data=f'deposit_{wallet_index}'),
            InlineKeyboardButton("🔒 Disconnect Wallet", callback_data=f'disconnect_{wallet_index}')
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f'sell_manage_{wallet_index}'),
            InlineKeyboardButton("⬅️ Back", callback_data='mainmenu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(full_message, reply_markup=reply_markup, parse_mode='Markdown')

# Function to display wallets menu
async def wallets_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.callback_query.from_user.id
    lang = user_languages.get(user_id, 'en')
    if user_id in user_wallets and user_wallets[user_id]:
        wallet_info = user_wallets[user_id][-1]
        welcome_message = get_welcome_message(wallet_info, lang)
        keyboard = [
            [InlineKeyboardButton("➕ New Wallet", callback_data='newwallet')],
            [InlineKeyboardButton("🔗 Connect Wallet", callback_data='connectwallet')],
            [InlineKeyboardButton("🔍 View Wallets", callback_data='viewwallets')],
            [InlineKeyboardButton("⬅️ Back", callback_data='mainmenu')]
        ]
    else:
        welcome_message = get_welcome_message(lang=lang)
        keyboard = [
            [InlineKeyboardButton("➕ Generate Wallet", callback_data='newwallet')],
            [InlineKeyboardButton("🔗 Connect Wallet", callback_data='connectwallet')],
            [InlineKeyboardButton("⬅️ Back", callback_data='mainmenu')],
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

# Function to generate and store a new wallet
async def generate_and_store_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.callback_query.from_user.id
    wallet_address, mnemonic = generate_wallet()

    # Store the wallet in the user's list
    if user_id not in user_wallets:
        user_wallets[user_id] = []
    user_wallets[user_id].append({
        "address": wallet_address,
        "mnemonic": mnemonic,
        "positions": {}  # Initialize empty positions
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

    await update.callback_query.edit_message_text(response_message, parse_mode='Markdown')
    await send_main_menu(update.callback_query.message, user_id)

# Function to display user's wallets
async def view_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.callback_query.from_user.id
    lang = user_languages.get(user_id, 'en')
    if user_id in user_wallets and user_wallets[user_id]:
        wallets = user_wallets[user_id]
        wallet_buttons = [
            [InlineKeyboardButton(f"Wallet {i+1}", callback_data=f'viewwallet_{i}')] for i in range(len(wallets))
        ]
        wallet_buttons.append([InlineKeyboardButton("⬅️ Back", callback_data='mainmenu')])
        reply_markup = InlineKeyboardMarkup(wallet_buttons)
        await update.callback_query.edit_message_text("Select a wallet to view:", reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await start(update, context)

# Function to view a specific wallet
async def view_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_index: str) -> None:
    user_id = update.callback_query.from_user.id
    wallet_index = int(wallet_index)
    lang = user_languages.get(user_id, 'en')
    if user_id in user_wallets and wallet_index < len(user_wallets[user_id]):
        wallet = user_wallets[user_id][wallet_index]
        wallet_info = wallet

        # Prepare positions text
        positions_text = "\n".join([f"{coin}: {amount} TON" for coin, amount in wallet["positions"].items()])
        if not positions_text:
            positions_text = "No positions added yet."

        new_text = (
            f"{get_welcome_message(wallet_info, lang)}\n\n"
            f"💼 **Your Positions:**\n{positions_text}\n\n"
        )
        new_reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💼 Sell and Manage 💼", callback_data=f'sell_manage_{wallet_index}')],
            [InlineKeyboardButton("❌ Delete Wallet", callback_data=f'deletewallet_{wallet_index}')],
            [InlineKeyboardButton("🔄 Refresh", callback_data=f'viewwallet_{wallet_index}')],
            [InlineKeyboardButton("⬅️ Back", callback_data='viewwallets')]
        ])
        await update.callback_query.edit_message_text(new_text, reply_markup=new_reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text("Invalid wallet index. Please select a valid wallet.")

# Function to display settings menu
async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.callback_query.from_user.id
    lang = user_languages.get(user_id, 'en')
    settings_message = {
        'en': "⚙️ **Settings**\n\nChoose an option to configure your wallet and bot settings.",
        'es': "⚙️ **Configuraciones**\n\nElige una opción para configurar tu billetera y ajustes del bot.",
        'ru': "⚙️ **Настройки**\n\nВыберите опцию для настройки вашего кошелька и параметров бота.",
        'fr': "⚙️ **Paramètres**\n\nChoisissez une option pour configurer votre portefeuille et les paramètres du bot.",
        'de': "⚙️ **Einstellungen**\n\nWählen Sie eine Option, um Ihre Wallet- und Bot-Einstellungen zu konfigurieren.",
        'pl': "⚙️ **Ustawienia**\n\nWybierz opcję, aby skonfigurować portfel i ustawienia bota."
    }
    keyboard = [
        [InlineKeyboardButton("🌐 Change Language", callback_data='change_language')],
        [InlineKeyboardButton("⬅️ Back", callback_data='mainmenu')]
    ]
    
    # Add delete wallet option only if there are wallets
    if user_id in user_wallets and user_wallets[user_id]:
        keyboard.insert(1, [InlineKeyboardButton("❌ Delete Wallet", callback_data='deletewallet')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(settings_message.get(lang, settings_message['en']), reply_markup=reply_markup, parse_mode='Markdown')

# Function to display change language menu
async def change_language_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.callback_query.from_user.id
    lang = user_languages.get(user_id, 'en')
    language_message = {
        'en': "🌐 **Change Language**\n\nSelect your preferred language:",
        'es': "🌐 **Cambiar Idioma**\n\nSelecciona tu idioma preferido:",
        'ru': "🌐 **Изменить язык**\n\nВыберите предпочитаемый язык:",
        'fr': "🌐 **Changer de langue**\n\nSélectionnez votre langue préférée :",
        'de': "🌐 **Sprache ändern**\n\nWählen Sie Ihre bevorzugte Sprache:",
        'pl': "🌐 **Zmień język**\n\nWybierz preferowany język:"
    }
    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data='set_lang_en'), InlineKeyboardButton("🇪🇸 Español", callback_data='set_lang_es')],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data='set_lang_ru'), InlineKeyboardButton("🇫🇷 Français", callback_data='set_lang_fr')],
        [InlineKeyboardButton("🇩🇪 Deutsch", callback_data='set_lang_de'), InlineKeyboardButton("🇵🇱 Polski", callback_data='set_lang_pl')],
        [InlineKeyboardButton("⬅️ Back", callback_data='settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(language_message.get(lang, language_message['en']), reply_markup=reply_markup, parse_mode='Markdown')

# Function to set the language
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    user_id = update.callback_query.from_user.id
    user_languages[user_id] = lang
    await update.callback_query.answer("Language changed successfully.")
    await settings_menu(update, context)

# Function to display delete wallet menu
async def delete_wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.callback_query.from_user.id
    if user_id in user_wallets and user_wallets[user_id]:
        wallet_buttons = [
            [InlineKeyboardButton(f"Wallet {i+1}", callback_data=f'deletewallet_{i}')] for i in range(len(user_wallets[user_id]))
        ]
        wallet_buttons.append([InlineKeyboardButton("⬅️ Back", callback_data='settings')])
        reply_markup = InlineKeyboardMarkup(wallet_buttons)
        await update.callback_query.edit_message_text("Select a wallet to delete:", reply_markup=reply_markup, parse_mode='Markdown')

# Function to add a position to a wallet
async def add_position(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    try:
        wallet_index = int(context.args[0])
        coin = context.args[1]
        amount = float(context.args[2])

        if user_id in user_wallets and wallet_index < len(user_wallets[user_id]):
            wallet = user_wallets[user_id][wallet_index]
            if coin in wallet["positions"]:
                wallet["positions"][coin] += amount
            else:
                wallet["positions"][coin] = amount
            await update.message.reply_text(f"Added {amount} TON to {coin} position.")
        else:
            await update.message.reply_text("Invalid wallet index.")

    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /addposition <wallet_index> <coin> <amount>")

# Function to handle the /addposition command
async def add_position_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await add_position(update, context)

# Function to delete a specific wallet
async def delete_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_index: str) -> None:
    user_id = update.callback_query.from_user.id
    wallet_index = int(wallet_index)
    if user_id in user_wallets and wallet_index < len(user_wallets[user_id]):
        del user_wallets[user_id][wallet_index]
        if not user_wallets[user_id]:
            del user_wallets[user_id]
            # Redirect to the start menu as no wallets are left
            await start(update, context)
        else:
            # Show the main menu with remaining wallets
            await send_main_menu(update.callback_query.message, user_id)

# Function to disconnect the wallet
async def disconnect_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_index: int) -> None:
    user_id = update.callback_query.from_user.id
    if user_id in user_wallets and wallet_index < len(user_wallets[user_id]):
        del user_wallets[user_id][wallet_index]
        if not user_wallets[user_id]:
            del user_wallets[user_id]
            # Redirect to the start menu as no wallets are left
            await start(update, context)
        else:
            # Show the main menu with remaining wallets
            await send_main_menu(update.callback_query.message, user_id)

# Function to connect an existing wallet
async def connect_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.edit_message_text("Please send your wallet address and seed phrase in the following format:\n/connect <wallet_address> <seed_phrase>", parse_mode='Markdown')

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
            "mnemonic": seed_phrase,
            "positions": {}  # Initialize empty positions
        })
        await update.message.reply_text(f"Wallet {wallet_address} connected successfully.", parse_mode='Markdown')
        await send_main_menu(update.message, user_id)
    except IndexError:
        await update.message.reply_text("Usage: /connect <wallet_address> <seed_phrase>")

# Function to deposit TON coins
async def deposit_ton(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_index: int) -> None:
    await update.callback_query.edit_message_text(
        "Please send the amount of TON and the wallet address in the following format:\n`/deposit <amount> <wallet_address>`",
        parse_mode='Markdown'
    )

# Function to withdraw all TON coins
async def withdraw_all_ton(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_index: int) -> None:
    await update.callback_query.edit_message_text(
        "Please send the destination wallet address in the following format:\n`/withdraw_all <wallet_address>`",
        parse_mode='Markdown'
    )

# Function to withdraw a specific amount of TON coins
async def withdraw_x_ton(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_index: int) -> None:
    await update.callback_query.edit_message_text(
        "Please send the amount and the destination wallet address in the following format:\n`/withdraw_x <amount> <wallet_address>`",
        parse_mode='Markdown'
    )

# Help function
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.callback_query.from_user.id
    lang = user_languages.get(user_id, 'en')
    help_text = {
        'en': (
            "Available commands:\n"
            "/start - Start the bot\n"
            "/home - Access the main menu\n"
            "/connect <wallet_address> <seed_phrase> - Connect an existing wallet\n"
            "/deposit <amount> <wallet_address> - Deposit TON coins\n"
            "/withdraw_all <wallet_address> - Withdraw all TON coins\n"
            "/withdraw_x <amount> <wallet_address> - Withdraw specific amount of TON coins\n"
            "/help - Show this help message\n"
        ),
        'es': (
            "Comandos disponibles:\n"
            "/start - Iniciar el bot\n"
            "/home - Acceder al menú principal\n"
            "/connect <wallet_address> <seed_phrase> - Conectar una billetera existente\n"
            "/deposit <amount> <wallet_address> - Depositar monedas TON\n"
            "/withdraw_all <wallet_address> - Retirar todas las monedas TON\n"
            "/withdraw_x <amount> <wallet_address> - Retirar una cantidad específica de monedas TON\n"
            "/help - Mostrar este mensaje de ayuda\n"
        ),
        'ru': (
            "Доступные команды:\n"
            "/start - Запустить бота\n"
            "/home - Доступ к главному меню\n"
            "/connect <wallet_address> <seed_phrase> - Подключить существующий кошелек\n"
            "/deposit <amount> <wallet_address> - Внести монеты TON\n"
            "/withdraw_all <wallet_address> - Вывести все монеты TON\n"
            "/withdraw_x <amount> <wallet_address> - Вывести определенное количество монет TON\n"
            "/help - Показать это сообщение с помощью\n"
        ),
        'fr': (
            "Commandes disponibles:\n"
            "/start - Démarrer le bot\n"
            "/home - Accéder au menu principal\n"
            "/connect <wallet_address> <seed_phrase> - Connecter un portefeuille existant\n"
            "/deposit <amount> <wallet_address> - Déposer des pièces TON\n"
            "/withdraw_all <wallet_address> - Retirer toutes les pièces TON\n"
            "/withdraw_x <amount> <wallet_address> - Retirer une quantité spécifique de pièces TON\n"
            "/help - Afficher ce message d'aide\n"
        ),
        'de': (
            "Verfügbare Befehle:\n"
            "/start - Den Bot starten\n"
            "/home - Zugriff auf das Hauptmenü\n"
            "/connect <wallet_address> <seed_phrase> - Vorhandenes Wallet verbinden\n"
            "/deposit <amount> <wallet_address> - TON-Münzen einzahlen\n"
            "/withdraw_all <wallet_address> - Alle TON-Münzen abheben\n"
            "/withdraw_x <amount> <wallet_address> - Eine bestimmte Menge an TON-Münzen abheben\n"
            "/help - Diese Hilfenachricht anzeigen\n"
        ),
        'pl': (
            "Dostępne komendy:\n"
            "/start - Uruchom bota\n"
            "/home - Dostęp do menu głównego\n"
            "/connect <wallet_address> <seed_phrase> - Połącz istniejący portfel\n"
            "/deposit <amount> <wallet_address> - Wpłać monety TON\n"
            "/withdraw_all <wallet_address> - Wypłać wszystkie monety TON\n"
            "/withdraw_x <amount> <wallet_address> - Wypłać określoną ilość monet TON\n"
            "/help - Pokaż tę wiadomość pomocy\n"
        )
    }
    keyboard = [
        [InlineKeyboardButton("⬅️ Back", callback_data='mainmenu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = help_text.get(lang, help_text['en'])

    if update.message:
        await update.message.reply_text(message, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)

# Function to handle messages containing a wallet address
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    wallet_address = update.message.text.strip()
    
    # Here you would fetch the relevant information about the wallet address
    # For now, let's assume we have fetched the data and create a dummy response
    coin_info = {
        'address': wallet_address,
        'price': '0.0000356 TON',
        'supply': '7.38K',
        'market_cap': '24.89K',
        'reserve': '7.38K',
        'volume': '5.35K',
        'pooled_ton': '564.47',
        'wallet_balance': '2.3296710 TON'
    }
    
    # Prepare the response message
    response_message = (
        f"📌 **Coin Information**\n\n"
        f"🔗 **Address:** `{coin_info['address']}`\n"
        f"💰 **Price:** {coin_info['price']}\n"
        f"🔄 **Supply:** {coin_info['supply']}\n"
        f"📊 **Market Cap:** {coin_info['market_cap']}\n"
        f"💵 **Reserve:** {coin_info['reserve']}\n"
        f"📈 **Volume (24h):** {coin_info['volume']}\n"
        f"💸 **Pooled TON:** {coin_info['pooled_ton']}\n"
        f"💼 **Wallet Balance:** {coin_info['wallet_balance']}\n\n"
        f"👇 **To buy, press one of the buttons below:**"
    )
    
    keyboard = [
        [InlineKeyboardButton("📈 Chart", callback_data=f'chart_{wallet_address}')],
        [InlineKeyboardButton("$ Buy 1 TON", callback_data=f'buy_1_{wallet_address}'), InlineKeyboardButton("$ Buy 5 TON", callback_data=f'buy_5_{wallet_address}')],
        [InlineKeyboardButton("$ Buy X TON", callback_data=f'buy_x_{wallet_address}')],
        [InlineKeyboardButton("🔄 Refresh", callback_data=f'refresh_{wallet_address}'), InlineKeyboardButton("⬅️ Back", callback_data=f'mainmenu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(response_message, reply_markup=reply_markup, parse_mode='Markdown')

# Function to send chart link
async def send_chart_link(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_address: str) -> None:
    chart_link = f"https://www.coingecko.com/en/coins/{wallet_address}"
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data=f'buy_{wallet_address}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        f"📈 **Chart Link**\n\n[Click here to view the chart]({chart_link})",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Function to handle buy commands
async def handle_buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str) -> None:
    parts = command.split('_')
    amount = parts[1]
    wallet_address = '_'.join(parts[2:])
    
    if amount == 'x':
        await update.callback_query.edit_message_text(
            f"Please send the amount of TON you want to buy for wallet address `{wallet_address}` in the following format:\n`/buy_x <amount>`",
            parse_mode='Markdown'
        )
    else:
        await update.callback_query.edit_message_text(
            f"You have chosen to buy {amount} TON for wallet address `{wallet_address}`.\nThis is a dummy implementation.",
            parse_mode='Markdown'
        )

# Function to refresh coin info
async def refresh_coin_info(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_address: str) -> None:
    # Dummy implementation of refreshing coin info
    await handle_message(update, context)

def main() -> None:
    application = Application.builder().token(TELEGRAM_API_KEY).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('home', home))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('connect', connect))
    application.add_handler(CommandHandler('addposition', add_position_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
