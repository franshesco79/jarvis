import os
import logging
import tempfile
from google import genai
from google.genai import types
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
    """Maneja las notas de voz entrantes."""
    try:
        # Avisar al usuario que está procesando para evitar que se corte la conexión
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")

        voice_file = await context.bot.get_file(update.message.voice.file_id)

        with tempfile.TemporaryDirectory() as tmp_dir:
            ogg_path = os.path.join(tmp_dir, "voice.ogg")
            mp3_path = os.path.join(tmp_dir, "response.mp3")

            # 1. Descargar la nota de voz
            await voice_file.download_to_drive(ogg_path)

            # 2. Leer el archivo en bytes
            with open(ogg_path, "rb") as f:
                audio_bytes = f.read()

            # 3. Enviar a Gemini
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[
                    types.Part.from_bytes(
                        data=audio_bytes,
                        mime_type="audio/ogg",
                    ),
                    "Escucha esta nota de voz y responde brevemente a lo que solicita.",
                ],
            )
            response_text = response.text if response.text else "No pude interpretar el audio."

            # 4. Convertir respuesta a audio con edge-tts
            communicate = edge_tts.Communicate(response_text, "es-ES-AlvaroNeural")
            await communicate.save(mp3_path)

            # 5. Responder con la nota de voz
            with open(mp3_path, "rb") as voice_out:
                await update.message.reply_voice(voice=voice_out)

    except Exception as e:
        logger.error(f"Error procesando audio: {e}")
        await update.message.reply_text("Lo siento, ocurrió un problema al procesar tu nota de voz.")


def main() -> None:
    """Inicia el bot de Telegram."""
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        raise ValueError("La variable de entorno TELEGRAM_BOT_TOKEN no está configurada.")

    # Configuración de la aplicación con timeouts extendidos para evitar cortes de red
    app = (
        Application.builder()
        .token(telegram_token)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .build()
    )

    # Registros de manejadores
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    logger.info("Jarvis iniciado y escuchando...")
    app.run_polling()


if __name__ == "__main__":
    main()
