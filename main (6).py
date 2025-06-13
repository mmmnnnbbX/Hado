
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telethon import TelegramClient
from telethon.sessions import StringSession

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توكن البوت
BOT_TOKEN = "8026503547:AAG7vCeuN6HNXHFg_ACwWhvmZM_cXY3oQ7M"

# حالات المحادثة
WAITING_FOR_API_ID, WAITING_FOR_API_HASH, WAITING_FOR_PHONE, WAITING_FOR_CODE, WAITING_FOR_PASSWORD = range(5)

# تخزين بيانات المستخدمين مؤقتاً
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة البداية مع الأزرار"""
    keyboard = [
        [InlineKeyboardButton("استخراج جلسة تيرمكس", callback_data='termux')],
        [InlineKeyboardButton("استخراج جلسة تليثيون", callback_data='telethon')],
        [InlineKeyboardButton("المطور", callback_data='developer')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_message = """🔐 مرحباً بك في بوت استخراج الجلسات

يوفر هذا البوت الجلسات الآمنة للحساب التي تتجنب التجميد

📱 نوع الجلسات المتاحة للاستخراج:
• تليثيون (Telethon)
• تيرمكس (Termux)

🛡️ مميزات البوت:
• جلسات آمنة من الهاتف المحمول
• تطبيق تلجرام الأصلي
• حماية من التجميد
• دعم متعدد الحسابات

اختر نوع الجلسة التي تريد استخراجها:"""

    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأزرار"""
    query = update.callback_query
    await query.answer()

    if query.data == 'developer':
        await query.edit_message_text("👨‍💻 المطور: @aqqaa")
        return ConversationHandler.END

    elif query.data in ['termux', 'telethon']:
        user_id = query.from_user.id
        user_data[user_id] = {'session_type': query.data}

        session_name = "تيرمكس" if query.data == 'termux' else "تليثيون"
        
        await query.edit_message_text(
            f"✅ تم اختيار استخراج جلسة {session_name}\n\n"
            "📝 الرجاء إرسال API ID الخاص بك:\n"
            "💡 يمكنك الحصول عليه من: https://my.telegram.org"
        )
        return WAITING_FOR_API_ID

async def get_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الحصول على API ID"""
    user_id = update.message.from_user.id
    api_id = update.message.text.strip()

    if not api_id.isdigit():
        await update.message.reply_text("❌ API ID يجب أن يكون رقم صحيح. الرجاء المحاولة مرة أخرى:")
        return WAITING_FOR_API_ID

    user_data[user_id]['api_id'] = int(api_id)
    await update.message.reply_text("📝 الرجاء إرسال API Hash الخاص بك:")
    return WAITING_FOR_API_HASH

async def get_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الحصول على API Hash"""
    user_id = update.message.from_user.id
    api_hash = update.message.text.strip()

    if len(api_hash) < 10:
        await update.message.reply_text("❌ API Hash غير صحيح. الرجاء المحاولة مرة أخرى:")
        return WAITING_FOR_API_HASH

    user_data[user_id]['api_hash'] = api_hash
    await update.message.reply_text("📱 الرجاء إرسال رقم الهاتف (مع رمز الدولة مثل +966xxxxxxxxx):")
    return WAITING_FOR_PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الحصول على رقم الهاتف"""
    user_id = update.message.from_user.id
    phone = update.message.text.strip()

    if not phone.startswith('+'):
        await update.message.reply_text("❌ يجب أن يبدأ رقم الهاتف بـ + متبوعاً برمز الدولة:")
        return WAITING_FOR_PHONE

    user_data[user_id]['phone'] = phone

    await update.message.reply_text("⏳ جاري إرسال رمز التحقق إلى رقم الهاتف...")

    try:
        # إنشاء عميل تلجرام مع معلومات جهاز أندرويد حقيقي
        client = TelegramClient(
            StringSession(), 
            user_data[user_id]['api_id'], 
            user_data[user_id]['api_hash'],
            device_model="Samsung SM-G973F",
            system_version="Android 11",
            app_version="9.2.1",
            lang_code="ar",
            system_lang_code="ar"
        )

        await client.connect()

        if not await client.is_user_authorized():
            # إرسال رمز التحقق
            result = await client.send_code_request(phone)
            user_data[user_id]['client'] = client
            user_data[user_id]['phone_code_hash'] = result.phone_code_hash

            await update.message.reply_text("✅ تم إرسال رمز التحقق إلى رقم الهاتف.\n📝 الرجاء إرسال الرمز:")
            return WAITING_FOR_CODE
        else:
            # المستخدم مسجل دخول بالفعل
            session_string = client.session.save()
            await send_session_to_user(update, user_id, session_string)
            await client.disconnect()
            del user_data[user_id]
            return ConversationHandler.END

    except Exception as e:
        logger.error(f"خطأ في إرسال الرمز: {str(e)}")
        await update.message.reply_text(f"❌ خطأ في إرسال الرمز: {str(e)}\n\nتأكد من صحة API ID و API Hash")
        if user_id in user_data:
            if 'client' in user_data[user_id]:
                try:
                    await user_data[user_id]['client'].disconnect()
                except:
                    pass
            del user_data[user_id]
        return ConversationHandler.END

async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الحصول على رمز التحقق"""
    user_id = update.message.from_user.id
    code = update.message.text.strip().replace(' ', '')

    if not code.isdigit() or len(code) < 5:
        await update.message.reply_text("❌ رمز التحقق يجب أن يكون أرقام فقط. الرجاء المحاولة مرة أخرى:")
        return WAITING_FOR_CODE

    try:
        client = user_data[user_id]['client']
        phone = user_data[user_id]['phone']
        phone_code_hash = user_data[user_id]['phone_code_hash']

        # تسجيل الدخول
        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        except Exception as e:
            error_msg = str(e).lower()
            if "two-step verification" in error_msg or "password" in error_msg:
                await update.message.reply_text("🔐 يتطلب حسابك كلمة مرور للمصادقة الثنائية.\n📝 الرجاء إرسالها:")
                return WAITING_FOR_PASSWORD
            elif "phone code invalid" in error_msg:
                await update.message.reply_text("❌ رمز التحقق غير صحيح. الرجاء المحاولة مرة أخرى:")
                return WAITING_FOR_CODE
            else:
                raise e

        # الحصول على الجلسة
        session_string = client.session.save()
        await send_session_to_user(update, user_id, session_string)

        # قطع الاتصال وتنظيف البيانات
        await client.disconnect()
        del user_data[user_id]

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"خطأ في تسجيل الدخول: {str(e)}")
        await update.message.reply_text(f"❌ خطأ في تسجيل الدخول: {str(e)}")
        if user_id in user_data and 'client' in user_data[user_id]:
            try:
                await user_data[user_id]['client'].disconnect()
            except:
                pass
            del user_data[user_id]
        return ConversationHandler.END

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الحصول على كلمة المرور للمصادقة الثنائية"""
    user_id = update.message.from_user.id
    password = update.message.text.strip()

    try:
        client = user_data[user_id]['client']

        # تسجيل الدخول بكلمة المرور
        await client.sign_in(password=password)

        # الحصول على الجلسة
        session_string = client.session.save()
        await send_session_to_user(update, user_id, session_string)

        # قطع الاتصال وتنظيف البيانات
        await client.disconnect()
        del user_data[user_id]

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"خطأ في كلمة المرور: {str(e)}")
        if "password invalid" in str(e).lower():
            await update.message.reply_text("❌ كلمة المرور غير صحيحة. الرجاء المحاولة مرة أخرى:")
            return WAITING_FOR_PASSWORD
        else:
            await update.message.reply_text(f"❌ خطأ في كلمة المرور: {str(e)}")
            if user_id in user_data and 'client' in user_data[user_id]:
                try:
                    await user_data[user_id]['client'].disconnect()
                except:
                    pass
                del user_data[user_id]
            return ConversationHandler.END

async def send_session_to_user(update: Update, user_id: int, session_string: str):
    """إرسال الجلسة للمستخدم بالتنسيق المناسب"""
    session_type = user_data[user_id]['session_type']

    if session_type == 'termux':
        formatted_session = f"""🔥 جلسة تيرمكس آمنة ومحمية 🔥

📱 نوع الجهاز: Samsung Galaxy S10
🤖 نظام التشغيل: Android 11
📲 إصدار التطبيق: Telegram 9.2.1
🛡️ محمية من التجميد

🔐 كود الجلسة:
```
{session_string}
```

⚠️ تعليمات الاستخدام:
1. انسخ الكود أعلاه
2. الصقه في ملف session.txt
3. استخدمه في سكريبت termux الخاص بك

✅ هذه الجلسة آمنة 100% ومحمية من التجميد"""

    else:  # telethon
        formatted_session = f"""🔥 جلسة تليثيون آمنة ومحمية 🔥

📱 نوع الجهاز: Samsung Galaxy S10  
🤖 نظام التشغيل: Android 11
📲 إصدار التطبيق: Telegram 9.2.1
🛡️ محمية من التجميد

🔐 كود الجلسة:
```
{session_string}
```

⚠️ تعليمات الاستخدام:
```python
from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = {user_data[user_id]['api_id']}
api_hash = '{user_data[user_id]['api_hash']}'
session = '{session_string}'

client = TelegramClient(StringSession(session), api_id, api_hash)
```

✅ هذه الجلسة آمنة 100% ومحمية من التجميد"""

    await update.message.reply_text(formatted_session, parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء العملية"""
    user_id = update.message.from_user.id
    if user_id in user_data:
        if 'client' in user_data[user_id]:
            try:
                await user_data[user_id]['client'].disconnect()
            except:
                pass
        del user_data[user_id]

    await update.message.reply_text("❌ تم إلغاء العملية.")
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الأخطاء العام"""
    logger.error(f"حدث خطأ: {context.error}")

def main():
    """تشغيل البوت"""
    print("🔄 جاري بدء تشغيل البوت...")

    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()

    # إعداد معالج المحادثة
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback, pattern='^(termux|telethon)$')],
        states={
            WAITING_FOR_API_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_id)],
            WAITING_FOR_API_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_hash)],
            WAITING_FOR_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            WAITING_FOR_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_code)],
            WAITING_FOR_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    # إضافة المعالجات
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_callback, pattern='^developer$'))
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)

    # تشغيل البوت
    print("✅ تم بدء تشغيل البوت بنجاح!")
    print("🤖 البوت جاهز لاستقبال الطلبات...")
    
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
