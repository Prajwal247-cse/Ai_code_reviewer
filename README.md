# 🤖 AI Code Reviewer — Powered by Google Gemini

> A production-grade AI-powered code review system using **Google Gemini API** — detects bugs, security vulnerabilities, performance issues, and bad practices with severity ranking, fix suggestions, and refactored code output.

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?style=flat-square&logo=fastapi)
![Gemini](https://img.shields.io/badge/LLM-Google%20Gemini-orange?style=flat-square&logo=google)
![License](https://img.shields.io/badge/license-MIT-purple?style=flat-square)

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 🐛 Bug Detection | Null pointers, logic errors, unchecked returns |
| 🔐 Security Analysis | SQL injection, XSS, hardcoded secrets, eval/exec |
| ⚡ Performance | Time complexity, memory leaks, inefficient patterns |
| 🤢 Code Smells | Mutable defaults, bare excepts, long functions |
| 🌀 Complexity | Cyclomatic complexity per function |
| 📘 Best Practices | Language-specific idioms |
| 🔧 Refactored Output | Full improved version of your code |
| 📊 Severity Ranking | critical / high / medium / low / info |
| 💯 Confidence Scores | Per-issue AI confidence (0–1) |
| 🌐 Multi-Language | Python, JavaScript, TypeScript, Java, Go, Rust, C++ |

---

## 🔑 Get Your FREE Google API Key

1. Go to **https://aistudio.google.com/app/apikey**
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key (starts with `AIza...`)
5. Paste it into `backend/.env` as `GOOGLE_API_KEY=AIza...`

> **Free tier**: 15 requests/minute, 1 million tokens/day — more than enough for development.

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
cd ai-code-reviewer/backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set your API key
```bash
cp .env.example .env
# Open .env and set: GOOGLE_API_KEY=AIzaSy-your-key-here
```

### 3. Start the server
```bash
uvicorn main:app --reload --port 8000
```

### 4. Open the UI
Open `frontend/index.html` in your browser.

---

## 🧠 Model Options

Set `LLM_MODEL` in your `.env`:

| Model | Speed | Quality | Use Case |
|-------|-------|---------|----------|
| `gemini-1.5-flash` | ⚡ Fast | ★★★★ | Daily use (default) |
| `gemini-1.5-pro` | 🐢 Slower | ★★★★★ | Deep reviews |
| `gemini-2.0-flash-exp` | ⚡ Fast | ★★★★★ | Latest features |

---

## 💻 CLI Usage

```bash
cd cli

# Review a Python file
python reviewer.py --file ../examples/bad_code.py --lang python

# Review JavaScript
python reviewer.py --file app.js --lang javascript

# Focus on security only
python reviewer.py --file server.py --lang python --focus security

# Save full JSON report
python reviewer.py --file main.go --lang go --output report.json
```

---

## 🐳 Docker

```bash
# Create a .env file in the project root with your key:
echo "GOOGLE_API_KEY=AIzaSy-your-key" > .env

cd docker
docker-compose up --build
# API: http://localhost:8000
# UI:  http://localhost:3000
```

---

## 📡 API Example

```bash
curl -X POST http://localhost:8000/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def foo(items=[]): return eval(items)",
    "language": "python",
    "include_refactor": true
  }'
```

---

## 📁 Project Structure

```
ai-code-reviewer/
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── requirements.txt         # google-generativeai + fastapi
│   ├── .env.example             # Template — copy to .env
│   ├── core/
│   │   ├── config.py            # GOOGLE_API_KEY, LLM_MODEL settings
│   │   └── models.py            # Pydantic schemas
│   ├── api/routes/
│   │   ├── review.py            # POST /api/v1/review
│   │   └── health.py            # GET /api/v1/health
│   ├── services/
│   │   ├── llm_service.py       # Google Gemini API calls
│   │   └── review_service.py    # Orchestration
│   ├── analyzers/
│   │   ├── python_analyzer.py   # Python AST + regex
│   │   └── generic_analyzer.py  # JS/Java/Go regex
│   └── tests/
│       └── test_reviewer.py
├── cli/
│   ├── reviewer.py              # CLI tool
│   └── github_bot.py           # GitHub PR bot
├── frontend/
│   └── index.html              # Web UI
├── vscode-extension/
│   ├── extension.js
│   └── package.json
└── docker/
    ├── Dockerfile.backend
    └── docker-compose.yml
```

---

## 🧪 Tests

```bash
cd backend
pytest tests/ -v
```

---

## ☁️ Deploy to Render (Free)

1. Fork this repo to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your repo
4. Settings:
   - Build: `pip install -r backend/requirements.txt`
   - Start: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add env var: `GOOGLE_API_KEY` = your key
6. Deploy!

---

*Built with FastAPI + Google Gemini + Python AST ❤️*
