import logging
import os
import time
import tempfile
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

import speech_recognition as sr
from pydub import AudioSegment
import openai

from config import Config

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Supported languages
LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ja': 'Japanese',
    'zh': 'Chinese',
    'hi': 'Hindi',
    'ar': 'Arabic',
    'ko': 'Korean',
    'nl': 'Dutch',
    'pl': 'Polish',
    'tr': 'Turkish',
    'vi': 'Vietnamese',
    'th': 'Thai',
    'id': 'Indonesian'
}

# Language codes for speech recognition
SR_LANGUAGES = {
    'en': 'en-US',
    'es': 'es-ES',
    'fr': 'fr-FR',
    'de': 'de-DE',
    'it': 'it-IT',
    'pt': 'pt-PT',
    'ru': 'ru-RU',
    'ja': 'ja-JP',
    'zh': 'zh-CN',
    'hi': 'hi-IN',
    'ar': 'ar-SA',
    'ko': 'ko-KR',
    'nl': 'nl-NL',
    'pl': 'pl-PL',
    'tr': 'tr-TR',
    'vi': 'vi-VN',
    'th': 'th-TH',
    'id': 'id-ID'
}

def convert_audio(input_path, output_format='wav'):
    """Convert audio to WAV format for processing"""
    try:
        audio = AudioSegment.from_file(input_path)
        output_path = f"{tempfile.mktemp()}.{output_format}"
        audio.export(output_path, format=output_format)
        return output_path
    except Exception as e:
        logger.error(f"Audio conversion error: {e}")
        return None

def transcribe_audio_google(audio_path, language='en-US'):
    """Transcribe audio using Google Speech Recognition"""
    try:
        recognizer = sr.Recognizer()
        
        with sr.AudioFile(audio_path) as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)
        
        # Recognize speech using Google
        text = recognizer.recognize_google(audio_data, language=language)
        return text
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        logger.error(f"Google Speech API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return None

def transcribe_audio_whisper(audio_path, language='en'):
    """Transcribe audio using OpenAI Whisper (requires API key)"""
    try:
        if not Config.OPENAI_API_KEY:
            return None
        
        with open(audio_path, 'rb') as audio_file:
            response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                language=language
            )
            return response.text
    except Exception as e:
        logger.error(f"Whisper API error: {e}")
        return None

def format_time(seconds):
    """Format time in seconds to MM:SS"""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🎤 Transcribe Audio", callback_data='transcribe'),
            InlineKeyboardButton("🌍 Set Language", callback_data='language')
        ],
        [
            InlineKeyboardButton("📊 History", callback_data='history'),
            InlineKeyboardButton("❓ Help", callback_data='help')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🎙️ *Welcome to Speak2Text Bot!*\n\n"
        "I convert voice messages and audio files to text.\n\n"
        "*How to use:*\n"
        "1. Send a voice message or audio file\n"
        "2. Choose the language (default: English)\n"
        "3. I'll transcribe it to text\n\n"
        "*Supported formats:*\n"
        "🎵 Voice messages\n"
        "🎵 MP3, WAV, OGG, M4A, FLAC\n\n"
        "*Supported languages:*\n"
        "English, Spanish, French, German, Italian,\n"
        "Portuguese, Russian, Japanese, Chinese, Hindi,\n"
        "and many more!\n\n"
        "Send me a voice message or audio file to start!"
    )
    
    if update.message:
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# Transcribe handler
async def transcribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "🎤 *Transcribe Audio*\n\n"
        "Send me a voice message or upload an audio file.\n\n"
        "*Supported formats:*\n"
        "• Voice messages (from Telegram)\n"
        "• MP3, WAV, OGG, M4A, FLAC\n\n"
        "*Tips for best results:*\n"
        "• Speak clearly and at a normal pace\n"
        "• Minimize background noise\n"
        "• Keep recordings under 5 minutes\n\n"
        "You can also set the language using /language\n"
        "before sending the audio."
    )
    
    await query.edit_message_text(text, parse_mode='Markdown')

# Language selection handler
async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if update.callback_query else None
    
    if query:
        await query.answer()
    
    # Create language selection keyboard
    keyboard = []
    lang_items = list(LANGUAGES.items())
    
    # Group languages in rows of 3
    for i in range(0, len(lang_items), 3):
        row = []
        for j in range(i, min(i+3, len(lang_items))):
            code, name = lang_items[j]
            current_lang = context.user_data.get('language', 'en')
            is_current = " ✅" if code == current_lang else ""
            row.append(InlineKeyboardButton(
                f"{name}{is_current}",
                callback_data=f'lang_{code}'
            ))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_lang = context.user_data.get('language', 'en')
    current_lang_name = LANGUAGES.get(current_lang, 'English')
    
    text = (
        f"🌍 *Select Language*\n\n"
        f"Current language: *{current_lang_name}*\n\n"
        "Choose the language of the audio you'll be sending.\n\n"
        "The bot will transcribe the audio in the selected language."
    )
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# History handler
async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    history = context.user_data.get('transcription_history', [])
    
    if not history:
        keyboard = [[InlineKeyboardButton("🎤 Transcribe Audio", callback_data='transcribe')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📊 *History*\n\n"
            "You haven't transcribed any audio yet.\n"
            "Send a voice message or audio file to get started!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Show last 5 transcriptions
    history_text = "*📊 Recent Transcriptions*\n\n"
    for i, entry in enumerate(reversed(history[-5:]), 1):
        text_preview = entry['text'][:50] + '...' if len(entry['text']) > 50 else entry['text']
        history_text += f"{i}. *{entry['language']}* ({entry['duration']})\n"
        history_text += f"   \"{text_preview}\"\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🗑️ Clear History", callback_data='clear_history')],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        history_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Clear history handler
async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['transcription_history'] = []
    
    await query.edit_message_text(
        "🗑️ *History Cleared!*\n\n"
        "All transcriptions have been removed.",
        parse_mode='Markdown'
    )

# Help handler
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    
    help_text = (
        "❓ *Help & Commands*\n\n"
        "*How to use:*\n"
        "1. Send a voice message or audio file\n"
        "2. Or use /transcribe for options\n"
        "3. Set language with /language\n\n"
        "*Commands:*\n"
        "/start - Show main menu\n"
        "/transcribe - Transcribe audio\n"
        "/language - Set language\n"
        "/history - View transcriptions\n"
        "/help - Show help\n"
        "/cancel - Cancel operation\n\n"
        "*Supported formats:*\n"
        "🎵 Voice messages\n"
        "🎵 MP3, WAV, OGG, M4A, FLAC\n\n"
        "*Supported languages:*\n"
        "18+ languages including:\n"
        "English, Spanish, French, German,\n"
        "Italian, Portuguese, Russian, Japanese,\n"
        "Chinese, Hindi, Arabic, Korean,\n"
        "Dutch, Polish, Turkish, Vietnamese,\n"
        "Thai, Indonesian\n\n"
        "*Tips:*\n"
        "• Keep audio under 5 minutes\n"
        "• Speak clearly\n"
        "• Minimize background noise\n"
        "• Set correct language for accuracy"
    )
    
    if query:
        await query.edit_message_text(help_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(help_text, parse_mode='Markdown')

# Cancel handler
async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['waiting_for_audio'] = False
    
    await update.message.reply_text(
        "❌ Operation cancelled.\n"
        "Type /start to go back to the main menu."
    )

# Main menu handler
async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(update, context)

# Handle audio messages
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages and audio files"""
    
    # Get the audio file
    if update.message.voice:
        audio_file = update.message.voice
        file_type = "voice"
        duration = audio_file.duration
    elif update.message.audio:
        audio_file = update.message.audio
        file_type = "audio"
        duration = audio_file.duration
    else:
        return
    
    # Check file size (max 20MB)
    if audio_file.file_size > 20 * 1024 * 1024:
        await update.message.reply_text(
            "❌ File too large! Maximum size is 20MB.\n"
            "Please send a shorter audio file."
        )
        return
    
    # Show processing message
    processing_msg = await update.message.reply_text(
        "⏳ Processing your audio... Please wait.\n\n"
        f"📏 Duration: {format_time(duration)}"
    )
    
    try:
        # Download the audio file
        file = await context.bot.get_file(audio_file.file_id)
        
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg' if file_type == 'voice' else '.mp3') as temp_file:
            await file.download_to_drive(temp_file.name)
            input_path = temp_file.name
        
        # Get language
        language = context.user_data.get('language', 'en')
        language_name = LANGUAGES.get(language, 'English')
        sr_language = SR_LANGUAGES.get(language, 'en-US')
        
        # Convert to WAV
        await processing_msg.edit_text(
            "🔄 Converting audio format...\n"
            f"📏 Duration: {format_time(duration)}"
        )
        
        wav_path = convert_audio(input_path)
        if not wav_path:
            await processing_msg.edit_text(
                "❌ Failed to convert audio. Please ensure the file is valid."
            )
            os.unlink(input_path)
            return
        
        # Transcribe
        await processing_msg.edit_text(
            "🎤 Transcribing audio...\n"
            f"📏 Duration: {format_time(duration)}\n"
            f"🌍 Language: {language_name}"
        )
        
        # Try Google Speech Recognition first
        text = transcribe_audio_google(wav_path, sr_language)
        
        # If Google fails, try Whisper
        if not text and Config.OPENAI_API_KEY:
            text = transcribe_audio_whisper(input_path, language)
        
        # Clean up files
        os.unlink(input_path)
        os.unlink(wav_path)
        
        if text:
            # Save to history
            if 'transcription_history' not in context.user_data:
                context.user_data['transcription_history'] = []
            
            context.user_data['transcription_history'].append({
                'text': text,
                'language': language_name,
                'duration': format_time(duration),
                'timestamp': time.time()
            })
            
            # Keep only last 50 entries
            if len(context.user_data['transcription_history']) > 50:
                context.user_data['transcription_history'] = context.user_data['transcription_history'][-50:]
            
            # Create response keyboard
            keyboard = [
                [
                    InlineKeyboardButton("📋 Copy", callback_data=f'copy_{text[:30]}'),
                    InlineKeyboardButton("🎤 Transcribe More", callback_data='transcribe')
                ],
                [
                    InlineKeyboardButton("🔙 Menu", callback_data='main_menu')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send transcription
            await processing_msg.edit_text(
                f"✅ *Transcription Complete!*\n\n"
                f"📏 Duration: {format_time(duration)}\n"
                f"🌍 Language: {language_name}\n\n"
                f"*Text:*\n"
                f"`{text}`\n\n"
                f"*Need a different language?* Use /language to change.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await processing_msg.edit_text(
                "❌ Failed to transcribe audio.\n\n"
                "Possible reasons:\n"
                "• Audio quality is poor\n"
                "• Language is not supported\n"
                "• Background noise is too loud\n"
                "• Audio is too long\n\n"
                "Try:\n"
                "• Speaking more clearly\n"
                "• Setting the correct language\n"
                "• Using a shorter audio file\n"
                "• Reducing background noise"
            )
            
    except Exception as e:
        logger.error(f"Audio processing error: {e}")
        await processing_msg.edit_text(
            f"❌ An error occurred: {str(e)}\n\n"
            "Please try again with a different audio file."
        )

# Copy handler
async def copy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_', 1)[1]
    
    await query.message.reply_text(
        f"📋 *Text copied to clipboard!*\n\n"
        f"`{data}`\n\n"
        f"*Note:* Please select and copy the text manually.",
        parse_mode='Markdown'
    )

# Language selection callback
async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    lang_code = query.data.split('_')[1]
    context.user_data['language'] = lang_code
    
    lang_name = LANGUAGES.get(lang_code, 'Unknown')
    
    await query.edit_message_text(
        f"✅ Language set to: *{lang_name}*\n\n"
        f"Now send me a voice message or audio file to transcribe!",
        parse_mode='Markdown'
    )

# Button handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == 'main_menu':
        await main_menu_handler(update, context)
    elif data == 'transcribe':
        await transcribe_handler(update, context)
    elif data == 'language':
        await language_handler(update, context)
    elif data == 'history':
        await history_handler(update, context)
    elif data == 'help':
        await help_handler(update, context)
    elif data == 'clear_history':
        await clear_history(update, context)
    elif data.startswith('lang_'):
        await language_callback(update, context)
    elif data.startswith('copy_'):
        await copy_handler(update, context)

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot"""
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("transcribe", transcribe_handler))
    application.add_handler(CommandHandler("language", language_handler))
    application.add_handler(CommandHandler("history", history_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("cancel", cancel_handler))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Message handlers
    application.add_handler(MessageHandler(
        filters.VOICE | filters.AUDIO, 
        handle_audio
    ))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    logger.info("🎙️ Audio Transcriber Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
