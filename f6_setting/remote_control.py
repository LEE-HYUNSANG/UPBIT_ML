import os
import importlib

try:
    telebot = importlib.import_module("telebot")
except Exception:  # pragma: no cover - optional dependency
    telebot = None

TOKEN = os.environ.get("TELEGRAM_TOKEN")
DEFAULT_STATUS_PATH = os.path.join(os.path.dirname(__file__), "server_status.txt")


def _status_file() -> str:
    """Return path to the server status file, allowing env override."""
    return os.environ.get("SERVER_STATUS_FILE", DEFAULT_STATUS_PATH)

bot = telebot.TeleBot(TOKEN) if telebot and TOKEN else None


def write_status(state: str) -> None:
    """Write ON/OFF state to the status file."""
    with open(_status_file(), "w", encoding="utf-8") as f:
        f.write(state)


def read_status() -> str:
    """Return current server state, defaults to OFF if file missing."""
    try:
        with open(_status_file(), "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "OFF"


if bot:
    @bot.message_handler(commands=["on"])
    def _handle_on(message):
        write_status("ON")
        bot.reply_to(message, "서버를 ON 했습니다.")

    @bot.message_handler(commands=["off"])
    def _handle_off(message):
        write_status("OFF")
        bot.reply_to(message, "서버를 OFF 했습니다.")

    @bot.message_handler(func=lambda m: True)
    def _handle_unknown(message):
        bot.reply_to(message, "명령어를 인식하지 못했습니다.\n/on 또는 /off를 사용하세요.")


def start_bot() -> None:
    """Start polling if telebot is available and token set."""
    if bot:
        bot.polling()
