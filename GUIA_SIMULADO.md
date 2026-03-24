# GUIA PASSO A PASSO - PROVA DE PROJETO DE SOFTWARE

## Visão Geral do que precisa ser feito

Criar uma API REST em Python (Flask) que se conecta ao MongoDB, com deploy automático via Docker + GitHub Actions na AWS.

---

## PARTE 1 — ESTRUTURA DO PROJETO (Arquivos que você precisa criar)

```
meu-projeto/
├── main.py                        ← Código da API (rotas)
├── requirements.txt               ← Dependências Python
├── Dockerfile                     ← Para criar imagem Docker
├── .gitignore                     ← Arquivos para o Git ignorar
└── .github/
    └── workflows/
        └── deploy.yml             ← Pipeline CI/CD do GitHub Actions
```

---

## PARTE 2 — CRIAÇÃO DA API (main.py)

### Passo 1: Imports e configuração
- Importar Flask, request, jsonify do flask
- Importar MongoClient do pymongo
- Importar datetime, uuid, requests, os
- Pegar variáveis de ambiente com `os.environ.get()` para MONGO_URL e USER_API_URL
- Criar o app Flask: `app = Flask(__name__)`
- Conectar ao MongoDB: `client = MongoClient(mongo_url)`
- Acessar banco e coleção: `db = client['posts_db']` e `posts_collection = db['posts']`

### Passo 2: Rota GET /post (listar posts)
- Decorador: `@app.route("/post", methods=["GET"])`
- Buscar todos os posts: `posts_collection.find({}, {"_id": 0})`
  - O `{"_id": 0}` remove o campo _id do MongoDB da resposta
- Converter para lista e retornar com `jsonify(posts), 200`

### Passo 3: Rota POST /post (criar post)
- Decorador: `@app.route("/post", methods=["POST"])`
- Pegar o ID do usuário do HEADER: `request.headers.get("usuario")`
- Se não veio o header, retornar erro 400
- **VALIDAR O USUÁRIO**: fazer um GET na API de usuários:
  - `requests.get(f"{user_api_url}/users/{user_id}")`
  - Se o status_code NÃO for 200/201, retornar erro 404
  - Colocar dentro de try/except para tratar erros de conexão
- Pegar dados do body: `data = request.json`
- Montar o dicionário do post com:
  - `id`: gerar com `str(uuid.uuid4())`
  - `titulo`: vem do body (`data["titulo"]`)
  - `mensagem`: vem do body (`data["mensagem"]`)
  - `data`: preencher no servidor com `datetime.now().isoformat()`
  - `usuario`: vem do header
- Inserir no MongoDB: `posts_collection.insert_one(post)`
- Remover o `_id` que o MongoDB adiciona: `post.pop("_id", None)`
- Retornar o post com `jsonify(post), 201`

### Passo 4: Bloco main
- `if __name__ == "__main__": app.run(debug=True, port=5002)`

---

## PARTE 3 — DEPENDÊNCIAS (requirements.txt)

Criar arquivo com:
```
Flask==2.3.3
pymongo==4.6.1
requests==2.31.0
```

- **Flask** → Framework web
- **pymongo** → Driver do MongoDB para Python
- **requests** → Para fazer chamadas HTTP (validar usuário)

---

## PARTE 4 — DOCKERFILE

Passo a passo do Dockerfile:

1. `FROM python:3.11-slim` → Imagem base do Python
2. `WORKDIR /app` → Define diretório de trabalho
3. `COPY requirements.txt .` → Copia o arquivo de dependências
4. `RUN pip install --no-cache-dir -r requirements.txt` → Instala dependências
5. `COPY . .` → Copia todo o código para dentro do container
6. `EXPOSE 5000` → Expõe a porta 5000
7. `ENV FLASK_APP=main.py` → Diz qual é o arquivo principal
8. `ENV FLASK_RUN_HOST=0.0.0.0` → Aceita conexões de qualquer IP
9. `CMD ["flask", "run"]` → Comando para executar a aplicação

---

## PARTE 5 — GITHUB ACTIONS (deploy.yml)

### Localização do arquivo
- DEVE ficar em `.github/workflows/deploy.yml` (exatamente esse caminho)

### Estrutura do workflow

1. **Trigger**: executa no push para branch `main`
   ```yaml
   on:
     push:
       branches: ["main"]
   ```

2. **Checkout do código**: `actions/checkout@v4`

3. **Setup Python**: `actions/setup-python@v3` com python-version "3.10"

4. **Instalar dependências**: `pip install -r requirements.txt`

5. **Login no Docker Hub**: `docker/login-action@v3`
   - username: `${{ secrets.DOCKER_USER }}`
   - password: `${{ secrets.DOCKERHUB_TOKEN }}`

6. **Setup Docker Buildx**: `docker/setup-buildx-action@v3`

7. **Build e Push da imagem**: `docker/build-push-action@v5`
   - context: `.`
   - file: `./Dockerfile`
   - push: `true`
   - tags: `${{ secrets.DOCKER_USER }}/posts-api:${{ github.sha }}`

8. **Deploy na AWS via SSH**: `appleboy/ssh-action@master`
   - host: `${{ secrets.HOST_TEST }}`
   - username: `"ubuntu"`
   - key: `${{ secrets.KEY_TEST }}`
   - Script que roda na AWS:
     - Para e remove container antigo (`docker stop` + `docker rm`)
     - Baixa a imagem nova (`docker pull`)
     - Roda o container novo (`docker run`) com variáveis de ambiente

---

## PARTE 6 — SECRETS DO GITHUB (Configurar no repositório)

Ir em: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name      | Valor                                            |
|------------------|--------------------------------------------------|
| DOCKER_USER      | seu usuário do Docker Hub                        |
| DOCKERHUB_TOKEN  | token de acesso do Docker Hub                    |
| HOST_TEST        | IP da AWS (ex: 18.230.76.235)                    |
| KEY_TEST         | chave SSH privada (.pem) para acessar a AWS      |
| MONGO_URL        | mongodb://mongo-connections:27017 (nome do container na rede) |
| USER_API_URL     | http://app_users:5000 (nome do container na rede)|

---

## PARTE 7 — INFRAESTRUTURA NA AWS (Rodar antes do deploy)

### Criar a rede Docker (se ainda não existe)
```bash
docker network create -d bridge rede
```

### Subir o MongoDB (se ainda não existe)
```bash
docker run -d --network=rede --name mongo-connections -p 27017:27017 mongo:7
```

### Verificar que a API de usuários já está rodando
```bash
docker ps
```
Deve aparecer o container da API de usuários conectado na rede `rede`.

---

## PARTE 8 — TESTAR A API

### Criar um post (com curl ou Postman):
```bash
curl -X POST http://18.230.76.235:5002/post \
  -H "Content-Type: application/json" \
  -H "usuario: ID-DO-USUARIO-AQUI" \
  -d '{"titulo": "Meu post", "mensagem": "Olá mundo!"}'
```

### Listar posts:
```bash
curl http://18.230.76.235:5002/post
```

### Testar com usuário inválido (deve retornar erro 404):
```bash
curl -X POST http://18.230.76.235:5002/post \
  -H "Content-Type: application/json" \
  -H "usuario: usuario-que-nao-existe" \
  -d '{"titulo": "Teste", "mensagem": "Não deveria funcionar"}'
```

---

## PARTE 9 — FLUXO COMPLETO DE DEPLOY (Resumão)

1. Escrever o código (main.py, requirements.txt, Dockerfile)
2. Criar o workflow em `.github/workflows/deploy.yml`
3. Configurar os Secrets no GitHub
4. Na AWS, garantir que a rede Docker e o MongoDB existem
5. Fazer `git add .` → `git commit` → `git push`
6. O GitHub Actions automaticamente:
   - Faz build da imagem Docker
   - Envia para o Docker Hub
   - Conecta via SSH na AWS
   - Para o container antigo
   - Sobe o container novo

---

## DICAS RÁPIDAS PARA A PROVA

- **Porta da API de posts**: 5002 (externa) → 5000 (interna no container)
- **MongoDB não precisa criar tabela**: ele cria automaticamente quando você insere
- **Header do usuário**: o campo `usuario` vai no HEADER HTTP, NÃO no body
- **Validação do usuário**: é um GET simples na API de users passando o ID
- **Data do post**: preencher no SERVIDOR com `datetime.now()`, não vem do cliente
- **UUID**: usar `uuid.uuid4()` para gerar ID único
- **Variáveis de ambiente**: usar `os.environ.get('NOME', 'valor_padrao')`
- **Docker network**: todos os containers precisam estar na mesma rede (`rede`)
- **Nomes DNS no Docker**: dentro da rede Docker, containers se comunicam pelo NOME do container (não por localhost)

---

## MAPA MENTAL - Como as peças se conectam

```
[Usuário/Postman]
       |
       | HTTP Request (Header: usuario)
       v
[API de Posts (Flask/Python)] ──── porta 5002
       |                |
       |                | GET /users/{id} (valida usuário)
       |                v
       |         [API de Usuários] ──── porta 5000/80
       |
       | Salva/Busca posts
       v
[MongoDB] ──── porta 27017
```

Todos os containers conectados na rede Docker "rede" e se comunicam pelos nomes dos containers.
