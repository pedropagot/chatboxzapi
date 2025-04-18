
from flask import Flask, request, jsonify
import re
import os
import requests

app = Flask(__name__)

ZAPI_INSTANCE_URL = os.environ.get("ZAPI_INSTANCE_URL")
ZAPI_SEND_ENDPOINT = f"{ZAPI_INSTANCE_URL}/send-message"

@app.route("/", methods=["GET"])
def home():
    return "Chatbot Z-API SEFAZ-MA está ativo!"

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    print(f"Payload recebido: {data}")

    incoming_msg = data.get("message", {}).get("body", "").strip().lower() if data else ""
    from_number = data.get("contact", {}).get("number", "") if data else ""
    
    if not incoming_msg or not from_number:
        return jsonify({"status": "ignored"})

    session = sessions.get(from_number, {"step": 0})
    step = session["step"]

    if step == -1 and any(greet in incoming_msg for greet in GREETINGS):
        session = {"step": 0}
        step = 0

    def send_message(text):
        payload = {
            "phone": from_number,
            "message": text
        }
        response = requests.post(ZAPI_SEND_ENDPOINT, json=payload)
        print(f"[Z-API RESPONSE] {response.status_code} - {response.text}")

    print(f"[RECEBIDO] De {from_number} - Etapa {step}: {incoming_msg}")

    if step == 0:
        if any(greet in incoming_msg for greet in GREETINGS):
            session["step"] = 1
            send_message("👋 Olá! Bem-vindo ao atendimento automatizado do setor de Trânsito.\n\n📌 Este canal é exclusivo para tratar de Mercadorias em Trânsito retidas em Postos Fiscais do Estado do Maranhão.\n\nAlguma mercadoria ou veículo foi retido em Posto Fiscal do Estado do Maranhão?\n[1] Sim\n[2] Não")
        else:
            send_message("Olá! Para iniciar o atendimento, por favor envie uma saudação como 'oi', 'olá', 'bom dia'...")

    elif step == 1:
        if incoming_msg == "1":
            session["step"] = 2
            send_message("Em qual Posto Fiscal está retida a mercadoria ou o veículo?\n[1] Estiva\n[2] Timon\n[3] Itinga\n[4] Quatro Bocas\n[5] Barão de Grajaú\n[6] Piranji\n[7] Estreito")
        elif incoming_msg == "2":
            send_message("❗Infelizmente não podemos atender a sua solicitação.\nEste canal é exclusivo para tratar de mercadorias em trânsito retidas em postos fiscais do Estado.\n\nMais informações: https://sistemas1.sefaz.ma.gov.br/portalsefaz/jsp/pagina/pagina.jsf?codigo=1585")
            session["step"] = -1
        else:
            send_message("Por favor, selecione uma opção válida: [1] Sim ou [2] Não")

    elif step == 2:
        if incoming_msg in [str(i) for i in range(1, 8)]:
            session["posto"] = incoming_msg
            session["step"] = 3
            send_message("Possui inscrição estadual?\n[1] Sim\n[2] Não")
        else:
            send_message("Por favor, selecione uma opção válida: [1] a [7]")

    elif step == 3:
        if incoming_msg == "1":
            session["step"] = 4
            send_message("Digite a sua inscrição estadual (apenas números):")
        elif incoming_msg == "2":
            session["step"] = 5
            send_message("Digite o CNPJ/CPF (apenas números):")
        else:
            send_message("Por favor, selecione uma opção válida: [1] Sim ou [2] Não")

    elif step == 4:
        if re.fullmatch(r"[\d\s.-]+", incoming_msg):
            session["ie"] = incoming_msg
            session["step"] = 6
            send_message("📝Por favor, relate brevemente a situação e, se necessário, envie os documentos relacionados (NFe, CTe, MDFe, etc.).")
        else:
            send_message("Por favor, digite apenas os números da inscrição estadual.")

    elif step == 5:
        if re.fullmatch(r"[\d\s.-]+", incoming_msg):
            session["cpf_cnpj"] = incoming_msg
            session["step"] = 6
            send_message("📝Por favor, relate brevemente a situação e, se necessário, envie os documentos relacionados (NFe, CTe, MDFe, etc.).")
        else:
            send_message("Por favor, digite apenas os números do CPF/CNPJ.")

    elif step == 6:
        session["relato"] = incoming_msg
        session["step"] = 7
        posto = session.get("posto", "[não informado]")
        identificador = session.get("ie") or session.get("cpf_cnpj") or "[não informado]"
        send_message(f"📨 Obrigado pelas informações!\n\nResumo do atendimento:\n- Posto Fiscal: {posto}\n- IE/CPF/CNPJ: {identificador}\n- Relato: {incoming_msg}\n\n🛠️ Seu atendimento foi encaminhado para análise da equipe interna.\n⏳ Em breve, um atendente entrará em contato.")
        session["step"] = -1

    sessions[from_number] = session
    return jsonify({"status": "ok"})

sessions = {}
GREETINGS = ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
