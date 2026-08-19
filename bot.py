import os
import logging
import tempfile
from google import genai
import edge_tts
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Configuración de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Inicialización del cliente de Gemini
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start."""
    await update.message.reply_text(
        "Saludos. Soy Jarvis, su asistente virtual. ¿En qué puedo ayudarle hoy?"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los mensajes de texto entrantes."""
    user_text = update.message.text
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=user_text,
    )
    await update.message.reply_text(response.text)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja las notas de voz entrantes."""
    voice_file = await context.bot.get_file(update.message.voice.file_id)

    with tempfile.TemporaryDirectory() as tmp_dir:
        ogg_path = os.path.join(tmp_dir, "voice.ogg")
        mp3_path = os.path.join(tmp_dir, "response.mp3")

        # Descargar la nota de voz a un archivo temporal local .ogg
        await voice_file.download_to_drive(ogg_path)

        # Subir archivo a Gemini usando client.files.upload(file=path)
        uploaded_file = client.files.upload(file=ogg_path)

        # Pasar el archivo a client.models.generate_content() con el modelo gemini-3.6-flash
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[uploaded_file, "Responde a esta nota de voz."],
        )

        # Convertir la respuesta de texto a voz con edge_tts.Communicate y guardarlo
        tts = edge_tts.Communicate(response.text, "es-ES-AlvaroNeural")
        await tts.save(mp3_path)

        # Responder al usuario con la nota de voz
        with open(mp3_path, "rb") as voice_out:
            await update.message.reply_voice(voice=voice_out)
        # Los archivos temporales se eliminan automáticamente al salir del bloque 'with'


def main() -> None:
    """Inicia el bot de Telegram."""
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        raise ValueError("La variable de entorno TELEGRAM_BOT_TOKEN no está configurada.")

    app = Application.builder().token(telegram_token).build()

    # Registros de manejadores
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Ejecución del bot
    app.run_polling()


if __name__ == "__main__":
    main()
