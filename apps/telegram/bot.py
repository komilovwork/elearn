import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from django.conf import settings
from django.db import transaction
from asgiref.sync import sync_to_async
from apps.base.redis_service import redis_service
from apps.user.models import User
import os
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Async database functions
@sync_to_async
def get_user_by_phone(phone_number):
    try:
        return User.objects.get(phone_number=phone_number)
    except User.DoesNotExist:
        return None

@sync_to_async
def get_user_by_tg_id(tg_user_id):
    try:
        return User.objects.get(tg_user_id=tg_user_id)
    except User.DoesNotExist:
        return None

@sync_to_async
def create_user(phone_number, first_name, last_name, tg_user_id=None, is_verified=False):
    return User.objects.create(
        phone_number=phone_number,
        first_name=first_name,
        last_name=last_name,
        tg_user_id=tg_user_id,
        is_verified=is_verified
    )

# Bot and dispatcher
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class UserStates(StatesGroup):
    waiting_for_contact = State()
    waiting_for_login = State()


def get_contact_keyboard():
    """Create keyboard for sharing contact"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Kontaktni ulashish", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_main_keyboard():
    """Create main menu keyboard"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/login")],
            [KeyboardButton(text="/help")]
        ],
        resize_keyboard=True
    )
    return keyboard


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Handle /start command"""
    await state.clear()
    
    welcome_text = """
🤖 *Xush kelibsiz!*

Bu bot orqali siz OTP kodi bilan tizimga kirishingiz mumkin.

Boshlash uchun kontaktni ulashing:
    """
    
    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_contact_keyboard()
    )
    await state.set_state(UserStates.waiting_for_contact)


@dp.message(StateFilter(UserStates.waiting_for_contact))
async def process_contact(message: types.Message, state: FSMContext):
    """Process shared contact"""
    if message.contact:
        phone_number = message.contact.phone_number
        
        # Remove + from phone number if present
        if phone_number.startswith('+'):
            phone_number = phone_number[1:]
        
        # Store phone number in state
        await state.update_data(phone_number=phone_number)
        
        # Check if user exists in database
        user = await get_user_by_phone(phone_number)
        
        if user:
            # Update user's tg_user_id if not set
            if not user.tg_user_id:
                user.tg_user_id = message.from_user.id
                await sync_to_async(user.save)()
            
            user_data = {
                'id': str(user.id),
                'phone_number': user.phone_number,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_verified': user.is_verified
            }
            await state.update_data(user_data=user_data)
            
            unknown_name = 'Noma\'lum'
            success_text = f"""
✅ *Kontakt qabul qilindi!*

Telefon raqam: `{phone_number}`
Ism: {user.first_name or unknown_name}

OTP kodi olish uchun /login buyrug'ini bosing."""
            
        else:
            # User doesn't exist, create temporary data
            user_data = {
                'phone_number': phone_number,
                'first_name': message.from_user.first_name or '',
                'last_name': message.from_user.last_name or '',
                'tg_user_id': message.from_user.id,
                'is_verified': False
            }
            await state.update_data(user_data=user_data)
            
            unknown_name = 'Noma\'lum'
            success_text = f"""
✅ *Kontakt qabul qilindi!*

Telefon raqam: `{phone_number}`
Ism: {message.from_user.first_name or unknown_name}

⚠️ *Eslatma:* Bu raqam tizimda ro'yxatdan o'tmagan. 
OTP kodi olish uchun /login buyrug'ini bosing.
            """
        
        await message.answer(
            success_text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        await state.set_state(UserStates.waiting_for_login)
        
    else:
        await message.answer(
            "❌ Iltimos, kontaktni to'g'ri ulashing!",
            reply_markup=get_contact_keyboard()
        )


@dp.message(Command("login"))
async def cmd_login(message: types.Message, state: FSMContext):
    """Handle /login command"""
    user_data = await state.get_data()
    phone_number = user_data.get('phone_number')
    
    # If no phone in state, try to get from database using tg_user_id
    if not phone_number:
        tg_user_id = message.from_user.id
        user = await get_user_by_tg_id(tg_user_id)
        
        if user and user.phone_number:
            phone_number = user.phone_number
            # Update state with phone number
            await state.update_data(phone_number=phone_number)
            
            # Update user data in state
            user_data = {
                'id': str(user.id),
                'phone_number': user.phone_number,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_verified': user.is_verified
            }
            await state.update_data(user_data=user_data)
        else:
            await message.answer(
                "❌ Avval kontaktni ulashing! /start buyrug'ini bosing.",
                reply_markup=get_contact_keyboard()
            )
            await state.set_state(UserStates.waiting_for_contact)
            return
    
    # Generate OTP
    otp = redis_service.generate_otp()
    
    # Store OTP in Redis
    success = redis_service.store_otp(phone_number, otp)
    
    if success:
        # Store user data in Redis for later use
        redis_service.store_user_data(phone_number, user_data.get('user_data', {}))
        
        otp_text = f"""
🔐 *OTP kodi yaratildi!*

Telefon raqam: `{phone_number}`
OTP kodi: `{otp}`

⏰ *Muddat:* 2 daqiqa
🔗 *Kirish:* {settings.TELEGRAM_WEBHOOK_URL}/login

Bu kodni login sahifasida kiriting.
        """
        
        await message.answer(
            otp_text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
    else:
        await message.answer(
            "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.",
            reply_markup=get_main_keyboard()
        )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Handle /help command"""
    help_text = """
📖 *Yordam*

*Buyruqlar:*
/start - Botni boshlash va kontakt ulashish
/login - OTP kodi olish
/help - Yordam

*Qadamlar:*
1️⃣ /start - Botni boshlang
2️⃣ Kontaktni ulashing
3️⃣ /login - OTP kodi oling
4️⃣ Login sahifasida OTP kodini kiriting
    """
    
    await message.answer(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


@dp.message()
async def handle_other_messages(message: types.Message, state: FSMContext):
    """Handle other messages"""
    current_state = await state.get_state()
    
    if current_state == UserStates.waiting_for_contact:
        await message.answer(
            "❌ Iltimos, kontaktni ulashing!",
            reply_markup=get_contact_keyboard()
        )
    elif current_state == UserStates.waiting_for_login:
        await message.answer(
            "ℹ️ OTP kodi olish uchun /login buyrug'ini bosing.",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            "❓ Noma'lum buyruq. /help yordam olish uchun.",
            reply_markup=get_main_keyboard()
        )


async def start_bot():
    """Start the bot"""
    try:
        logger.info("Starting Telegram bot...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")


if __name__ == "__main__":
    asyncio.run(start_bot())
