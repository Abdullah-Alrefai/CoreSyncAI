
# CoreSync AI (Demo)

A Streamlit app to track workouts, calories/protein, visualize a simple muscle heatmap, and chat with an AI assistant.

## Features
- **Login** (demo): `testuser` / `test123`
- **Workouts**: log exercise with muscle group, month view, body heatmap
- **Calories**: log food with calories/protein (required) and optional macros; daily analytics
- **Chatbot**: uses OpenAI if `OPENAI_API_KEY` is set; otherwise shows a local demo response

## Run locally
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

If you have an OpenAI API key:
```bash
export OPENAI_API_KEY="sk-..."
# or on Windows Powershell
setx OPENAI_API_KEY "sk-..."
```
