
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

user_sessions = {}

ZAPI_INSTANCE_ID = os.environ.get("ZAPI_INSTANCE_ID")
ZAPI_CLIENT_TOKEN = os.environ.get("ZAPI_CLIENT_TOKEN")
ZAPI_SEND_ENDPOINT = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_CLIENT_TOKEN}/send-messages"
headers = {}
print(f"📤 URL final usada: {ZAPI_SEND_ENDPOINT}", flush=True)
print(f"🛡️ Header usado: {headers}", flush=True)

mensagem_boas_vindas = """👋 Olá! Bem-vindo ao atendimento automatizado do setor de Trânsito.

📌 Este canal de comunicação é exclusivo para tratar de *Mercadorias em Trânsito* retidas em Postos Fiscais do Estado do Maranhão.

Alguma mercadoria ou veículo foi retido em Posto Fiscal do Estado do Maranhão?
[1] Sim   
[2] Não"""

mensagem_final_redirecionamento = "✅ Atendimento encerrado. Para outras dúvidas, acesse o site da Sefaz-MA: https://sistemas.sefaz.ma.gov.br"

@app.route("/", methods=["GET"])
def home():
    return "🟢 Chatbot está ativo!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    # Compatível com JSON da Z-API
    user_id = data.get("user") or data.get("contact", {}).get("number")
    message_raw = data.get("message")
    if isinstance(message_raw, dict):
        message_raw = message_raw.get("body")

    print(f"📥 Mensagem recebida: {message_raw} ({type(message_raw)})", flush=True)

    if not user_id:
        return jsonify({"status": "erro", "mensagem": "ID do usuário não fornecido"}), 400

    if isinstance(message_raw, str):
        message = message_raw.strip().lower()
    else:
        return jsonify({"status": "erro", "mensagem": "Formato de mensagem inválido"}), 400

    session = user_sessions.get(user_id, {"etapa": 0})

    if session["etapa"] == 0:
        if any(msg in message for msg in ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"]):
            send_message(user_id, mensagem_boas_vindas)
            session["etapa"] = 1
        else:
            return jsonify({"status": "aguardando_saudacao"}), 200

    elif session["etapa"] == 1:
        if message == "1":
            send_message(user_id, "🔎 Por favor, informe o nome do Posto Fiscal onde ocorreu a retenção.")
            session["etapa"] = 2
        elif message == "2":
            send_message(user_id, mensagem_final_redirecionamento)
            session["etapa"] = 99
        else:
            send_message(user_id, "❗ Por favor, responda com [1] para SIM ou [2] para NÃO.")

    elif session["etapa"] == 2:
        session["posto_fiscal"] = message
        send_message(user_id, "📄 A empresa possui inscrição estadual no Maranhão? Responda com [1] Sim ou [2] Não.")
        session["etapa"] = 3

    elif session["etapa"] == 3:
        if message == "1":
            send_message(user_id, "🔢 Digite o número da inscrição estadual.")
            session["etapa"] = 4
        elif message == "2":
            send_message(user_id, "🆔 Então, informe o número do CNPJ ou CPF.")
            session["etapa"] = 5
        else:
            send_message(user_id, "❗ Responda apenas com [1] ou [2].")

    elif session["etapa"] == 4:
        if message.isdigit():
            session["inscricao_estadual"] = message
            send_message(user_id, "✍️ Por favor, escreva um breve relato sobre a situação.")
            session["etapa"] = 6
        else:
            send_message(user_id, "❗ Digite apenas números. Tente novamente.")

    elif session["etapa"] == 5:
        if message.isdigit():
            session["cpf_cnpj"] = message
            send_message(user_id, "✍️ Por favor, escreva um breve relato sobre a situação.")
            session["etapa"] = 6
        else:
            send_message(user_id, "❗ Digite apenas números. Tente novamente.")

    elif session["etapa"] == 6:
        session["relato"] = message
        resumo = f"""✅ Atendimento registrado com sucesso!

📍 *Posto Fiscal:* {session.get('posto_fiscal')}
🆔 *IE ou CPF/CNPJ:* {session.get('inscricao_estadual', session.get('cpf_cnpj'))}
📝 *Relato:* {session.get('relato')}

📎 Encaminhe agora os documentos pertinentes para análise."""
        send_message(user_id, resumo)
        session["etapa"] = 99

    user_sessions[user_id] = session
    return jsonify({"status": "ok"}), 200

def send_message(user, text):
    payload = {
        "phone": user,
        "message": text
    }
    try:
        response = requests.post(ZAPI_SEND_ENDPOINT, json=payload)
        print(f"📨 Payload enviado: {payload}", flush=True)
        print(f"📬 Resposta da Z-API: {response.status_code} - {response.text}", flush=True)
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem: {e}", flush=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
