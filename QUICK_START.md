# 🚀 VITALIS - Quick Start Guide

## Choose Your Path

### 🟢 **Path A: I just want to start it** (5 min)
```bash
# Windows
start_vitalis.bat

# macOS/Linux  
bash start_vitalis.sh
```
⚠️ **Warning:** Will fail if credentials/tokens missing. See Path C.

---

### 🟡 **Path B: Verify everything first** (15 min) ← RECOMMENDED
```bash
# PowerShell
.\Verificar-Vitalis.ps1

# Or Python
python verificar_vitalis.py

# Then follow the suggestions
start_vitalis_v2.bat
```
✅ **Best:** Tells you EXACTLY what's missing.

---

### 🔴 **Path C: Full Setup from Scratch** (30 min)
```bash
# 1. Install dependencies
npm install
cd backend && pip install -r requirements.txt && cd ..

# 2. Create .env with API key (choose ONE)
cd backend
echo GROQ_API_KEY=gsk_XXXXXXXXXXXX > .env
# OR
echo GEMINI_API_KEY=AIzaXXXXXXXXXX > .env
cd ..

# 3. Create database
cd backend && python init_db_script.py && cd ..

# 4. (Optional) Add Garmin tokens to backend/.garth/
# oauth1_token.json
# oauth2_token.json

# 5. Start
start_vitalis.bat
```

---

## What gets created?

```
Frontend:  http://localhost:5173  (React UI)
Backend:   http://localhost:8001  (FastAPI)
API Docs:  http://localhost:8001/docs
```

---

## Components Status After Startup

| Feature | Status | What to Check |
|---------|--------|---------------|
| UI Loads | ✅ | Go to http://localhost:5173 |
| Backend Responds | ✅ | `curl http://localhost:8001/health` |
| Chat Works | ❓ | Type "hello" - should respond in 10-30s |
| Garmin Sync | ❓ | Need tokens in `.garth/` |

---

## Stop Everything

```bash
# Windows
stop_vitalis.bat

# macOS/Linux
Ctrl+C in terminals
```

---

## Help!

- **Something isn't working?** → Read `TROUBLESHOOTING.md`
- **Want full details?** → Read `VERIFICACION_VITALIS.md`
- **Need setup help?** → Read `README_VERIFICACION.md`

---

**👉 Start with `.\Verificar-Vitalis.ps1` - It will tell you exactly what you need!**
