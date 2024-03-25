import os
import shutil
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import ffmpegio
from dotenv import load_dotenv
# Ensure the 'audio' directory exists in the current project
audio_dir = os.path.join(os.getcwd(), 'audio')
if not os.path.exists(audio_dir):
    os.makedirs(audio_dir)
# Dictionary to store chat states and captions
chat_states = {}
# Load environment variables from a .env file (if you're using python-dotenv)
load_dotenv()
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Send me a caption for your audio file, and then send the audio file.')
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Store the caption and notify the user
    chat_id = update.message.chat_id
    chat_states[chat_id] = update.message.text
    print(f"Caption stored for chat {chat_id}: {chat_states[chat_id]}")  # Debug print
    await update.message.reply_text('Got it! Now, send me the audio file.')
def clear_audio_directory(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)  # Be careful, this deletes directories
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id

    # Debug print to check if the caption exists for the chat_id
    # print(f"Chat states before retrieving caption: {chat_states}")
    
    # Check if there's a caption stored for this chat
    caption = chat_states.pop(chat_id, "No caption provided.")
    # print(f"Using caption for chat {chat_id}: {caption}")  # Debug print
    # Retrieve audio file
    audio_file = update.message.audio or update.message.voice
    if not audio_file:
        await update.message.reply_text("Please send an audio file.")
        return

    # Asynchronously obtain the File object
    file = await audio_file.get_file()
    
    # Define the path for saving the audio file dynamically in its original format
    audio_file_path_original = os.path.join('audio', f"{file.file_unique_id}.{audio_file.file_name.split('.')[-1]}")
    
    # Define the path for the converted audio file in ogg format
    audio_file_path_ogg = os.path.join('audio', f"{file.file_unique_id}.ogg")
        
    # Await the get_file coroutine and then download the file
    await file.download_to_drive(custom_path=audio_file_path_original)

    # Correct usage of ffmpegio.transcode to match the ffmpeg command
    try:
        # Convert the audio file to ogg format using libopus codec with a bitrate of 16k
        ffmpegio.transcode(
            audio_file_path_original, 
            audio_file_path_ogg, 
            show_log=True,
            **{'vn': None, 'c:a': 'libopus', 'b:a': '16k'}
        )
    except Exception as e:
        await update.message.reply_text("Sorry, there was an error processing your audio file.")
        print(f"Error converting audio file: {e}")
        return

    # After converting, send the audio file as a voice message
    with open(audio_file_path_ogg, 'rb') as audio:
        await update.message.reply_voice(
            voice=audio,
            caption=caption,
            read_timeout=120,
            write_timeout=120
        )

    # Clear the audio directory after sending the file
    clear_audio_directory(audio_dir)

def main() -> None:
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables")
    application = ApplicationBuilder().token(token).build()
    text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    application.add_handler(text_handler)

    start_handler = CommandHandler('start', start)
    audio_handler = MessageHandler(filters.AUDIO | filters.VOICE, handle_audio)

    application.add_handler(start_handler)
    application.add_handler(audio_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
