from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
import uuid
import requests
import os
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
USER_API_URL = os.environ.get('USER_API_URL', 'http://18.228.48.67')

app = Flask(__name__)
client = MongoClient(MONGO_URL)
db = client['transacoes_db']
transacoes_collection = db['transacoes']

@app.route("/transacao", methods=["GET"])
def get_transacoes():
    id_cliente = request.args.get('id_cliente')
    query = {}
    if id_cliente:
        query = {"id_cliente": id_cliente}
        
    transacoes = list(transacoes_collection.find(query, {"_id": 0}))
    if not transacoes:
        return jsonify({"mensagem": "Nenhuma transação encontrada."}), 404
        
    return jsonify(transacoes), 200

@app.route("/transacao/<string:id>", methods=["DELETE"])
def delete_transacao(id):
    result = transacoes_collection.delete_one({"id": id})

    if result.deleted_count == 0:
        return jsonify({"mensagem": "Transação não encontrada."}), 404
        
    return jsonify({"mensagem": "Transação deletada com sucesso."}), 200

@app.route("/transacao", methods=["POST"])
def create_transacao():
    data = request.get_json()
    if not data:
        return jsonify({"mensagem": "Corpo da requisição inválido. Forneça um JSON."}), 400

    required_fields = ["id_cliente", "codigo_acao", "quantidade", "preco_unitario"]
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"mensagem": f"Campo '{field}' é obrigatório."}), 400

    id_cliente = data["id_cliente"]
    codigo_acao = data["codigo_acao"]
    quantidade = data["quantidade"]
    preco_unitario = data["preco_unitario"]

    try:
        user_response = requests.get(f"{USER_API_URL}/users/{id_cliente}")
        user_response.raise_for_status()
        user_data = user_response.json()
        user_email = user_data.get("email")
        if not user_email:
            return jsonify({"mensagem": "E-mail do usuário não encontrado na API de usuários."}), 500
    except requests.exceptions.RequestException as e:
        if e.response and e.response.status_code == 404:
            return jsonify({"mensagem": f"Cliente com id '{id_cliente}' não encontrado."}), 404
        else:
            return jsonify({"mensagem": f"Erro ao comunicar com a API de usuários: {str(e)}"}), 500

    try:
        valor_total = quantidade * preco_unitario
    except TypeError:
        return jsonify({"mensagem": "Campos 'quantidade' e 'preco_unitario' devem ser números válidos."}), 400

    nova_transacao = {
        "id": str(uuid.uuid4()),
        "id_cliente": id_cliente,
        "nome_cliente": user_data.get("name"),
        "email_cliente": user_email,
        "codigo_acao": codigo_acao,
        "quantidade": quantidade,
        "preco_unitario": preco_unitario,
        "valor_total": valor_total,
        "data_transacao": datetime.now().isoformat()
    }

    try:
        transacoes_collection.insert_one(nova_transacao)
        nova_transacao.pop("_id", None) 
        return jsonify(nova_transacao), 201
    except Exception as e:
        return jsonify({"mensagem": f"Erro ao salvar a transação no banco de dados: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=500)