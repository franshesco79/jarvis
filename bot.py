import os
import logging
import tempfile
from google import genai
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
    try:
        user_text = update.message.text
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=user_text,
        )
        await update.message.reply_text(response.text)
    except Exception as e:
        logger.error(f"Error procesando texto: {e}")
        await update.message.reply_text("Ocurrió un error al procesar el texto.")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja las notas de voz entrantes y responde con texto."""
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        voice_file = await context.bot.get_file(update.message.voice.file_id)

        with tempfile.TemporaryDirectory() as tmp_dir:
            ogg_path = os.path.join(tmp_dir, "voice.ogg")
            await voice_file.download_to_drive(ogg_path)

            # Subir audio a Gemini
            uploaded_file = client.files.upload(file=ogg_path)

            # Generar respuesta de texto a partir del audio
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[uploaded_file, "Escucha esta nota de voz y responde a lo que solicita de forma clara."],
            )
            response_text = response.text if response.text else "No pude interpretar el audio."

            # Enviar la respuesta en texto
            await update.message.reply_text(response_text)

    except Exception as e:
        logger.error("Error detallado procesando audio:", exc_info=True)
        await update.message.reply_text(f"Error procesando nota de voz: {str(e)}")


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

    logger.info("Jarvis iniciado y escuchando...")
    app.run_polling()


if __name__ == "__main__":
    main()
