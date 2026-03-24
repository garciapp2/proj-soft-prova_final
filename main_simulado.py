from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
import uuid
import requests
import os

mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
user_api_url = os.environ.get('USER_API_URL', 'http://localhost:5001')

app = Flask(__name__)

client = MongoClient(mongo_url)
db = client['posts_db']
posts_collection = db['posts']


@app.route("/post", methods=["GET"])
def list_posts():
    posts = list(posts_collection.find({}, {"_id": 0}))
    return jsonify(posts), 200


@app.route("/post", methods=["POST"])
def create_post():
    user_id = request.headers.get("usuario")

    if not user_id:
        return jsonify({"error": "Header 'usuario' é obrigatório"}), 400

    try:
        response = requests.get(f"{user_api_url}/users/{user_id}")
        if response.status_code not in (200, 201):
            return jsonify({"error": "Usuário não encontrado"}), 404
    except requests.exceptions.RequestException:
        return jsonify({"error": "Erro ao validar usuário"}), 500

    data = request.json

    post = {
        "id": str(uuid.uuid4()),
        "titulo": data["titulo"],
        "mensagem": data["mensagem"],
        "data": datetime.now().isoformat(),
        "usuario": user_id
    }

    posts_collection.insert_one(post)
    post.pop("_id", None)

    return jsonify(post), 201


if __name__ == "__main__":
    app.run(debug=True, port=5002)
