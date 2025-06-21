from flask import Flask, request, render_template, redirect, url_for, session, jsonify, send_from_directory
from authlib.integrations.flask_client import OAuth
from db import init_db, get_or_create_user
from memory import save_message, get_memory
from ai import generate_response
from flask_session import Session
import os
import sqlite3
from werkzeug.utils import secure_filename
import io
from PyPDF2 import PdfReader
import docx
from dotenv import load_dotenv

load_dotenv()

# --- AGENT CONFIGURATION ---
AGENTS = {
    "generalist": {
        "name": "Generalist",
        "prompt": "You are a helpful general-purpose AI assistant. Be friendly, knowledgeable, and ready to help with a wide range of tasks.",
        "description": "The default, all-purpose AI for any question.",
    },
    "creative_writer": {
        "name": "Creative Writer",
        "prompt": "You are a master storyteller and creative writer. Your purpose is to help users write poems, stories, marketing copy, and other creative texts. Always adopt a highly imaginative and descriptive tone.",
        "description": "Your partner for stories, poems, and marketing copy.",
    },
    "code_assistant": {
        "name": "Code Assistant",
        "prompt": "You are an expert programmer and code assistant. Your goal is to help users write, debug, and understand code. Provide clear explanations and always format code snippets correctly in markdown.",
        "description": "The expert for writing, debugging, and explaining code.",
    },
    "travel_planner": {
        "name": "Travel Planner",
        "prompt": "You are a knowledgeable travel agent. Your job is to create detailed itineraries, suggest destinations, and provide practical travel advice. Always be enthusiastic and helpful.",
        "description": "Plan your next adventure with itineraries and advice.",
    },
    "career_coach": {
        "name": "Career Coach",
        "prompt": "You are a supportive and insightful career coach. You help users with resume writing, interview preparation, and career advice. Be encouraging and provide actionable tips.",
        "description": "Get help with resumes, interview prep, and career advice.",
    },
    "chef": {
        "name": "Chef",
        "prompt": "You are a passionate chef and culinary expert. You provide recipes, create meal plans, and offer cooking guidance. Your tone should be warm and your instructions easy to follow.",
        "description": "Discover new recipes, meal plans, and cooking tips.",
    },
    "fitness_trainer": {
        "name": "Fitness Trainer",
        "prompt": "You are a certified fitness trainer. Your role is to create workout plans, offer fitness advice, and motivate users to reach their health goals. Be energetic and knowledgeable.",
        "description": "Your guide to workout plans and achieving fitness goals.",
    }
}

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')
app.config.from_mapping(
    SESSION_TYPE='filesystem',
    GOOGLE_CLIENT_ID=os.environ.get("GOOGLE_CLIENT_ID"),
    GOOGLE_CLIENT_SECRET=os.environ.get("GOOGLE_CLIENT_SECRET"),
)
Session(app)
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=app.config["GOOGLE_CLIENT_ID"],
    client_secret=app.config["GOOGLE_CLIENT_SECRET"],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

init_db()

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri, prompt='select_account')

@app.route('/authorize')
def authorize():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    if user_info:
      session['user'] = user_info
    return redirect('/')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('agent', None) # Clear agent on logout
    return redirect('/')

@app.route("/agent/<agent_name>")
def set_agent(agent_name):
    if "user" not in session:
        return redirect(url_for("login"))
    
    # Set the agent
    if agent_name in AGENTS:
        session['agent'] = agent_name
    else:
        session['agent'] = 'generalist'
        
    # Clear the history for a new conversation with the selected agent
    user_info = session.get("user")
    username = user_info.get("name", "User")
    user_id = get_or_create_user(username)
    conn = sqlite3.connect('dip_users.db')
    c = conn.cursor()
    c.execute('DELETE FROM memories WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('chat'))

@app.route("/", methods=["GET", "POST"])
def chat():
    if "user" not in session:
        return render_template("landing.html", agents=AGENTS)

    user_info = session["user"]
    username = user_info.get('name', 'User')
    user_id = get_or_create_user(username)
    memory = get_memory(user_id)
    
    # --- Agent Handling ---
    current_agent_name = session.get('agent', 'generalist')
    current_agent = AGENTS.get(current_agent_name, AGENTS['generalist'])

    if request.method == "POST":
        user_input = request.form.get("message", "")
        file = request.files.get("file")
        file_content = None

        if file and file.filename:
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1].lower()
            if ext == ".txt":
                file_content = file.read().decode("utf-8", errors="ignore")
            elif ext == ".pdf":
                pdf = PdfReader(file)
                file_content = " ".join(page.extract_text() or '' for page in pdf.pages)
            elif ext == ".docx":
                doc = docx.Document(io.BytesIO(file.read()))
                file_content = " ".join([p.text for p in doc.paragraphs])
            
            if file_content:
                instruction = (
                    f"Please summarize and analyze the following file for key points, important dates, and any actions required.\\n"
                    f"File name: {filename}\\n---\\n"
                )
                if user_input.strip():
                    user_input = (
                        f"{instruction}User's question: {user_input.strip()}\\n(Attached file content below)\\n{file_content[:1500]}"
                    )
                else:
                    user_input = (
                        f"{instruction}(Attached file content below)\\n{file_content[:1500]}"
                    )

        if user_input:
            save_message(user_id, f"User: {user_input}")
            # Prepend agent's system prompt to the AI query
            system_prompt = current_agent['prompt']
            ai_query = f"{system_prompt}\n\n{user_input}"
            response = generate_response(ai_query, memory)
            save_message(user_id, f"AI: {response}")
            memory = get_memory(user_id) # Refresh memory

    return render_template("chat.html", username=username, memory=memory, agent=current_agent, agents=AGENTS)

@app.route("/new_chat", methods=["POST", "GET"])
def new_chat():
    if "user" not in session:
        return redirect(url_for("login"))
    
    user_info = session.get("user")
    if not user_info:
        return redirect(url_for("login"))

    # New chats from the UI button reset to the generalist agent
    session['agent'] = 'generalist'

    username = user_info.get("name", "User")
    user_id = get_or_create_user(username)
    conn = sqlite3.connect('dip_users.db')
    c = conn.cursor()
    c.execute('DELETE FROM memories WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for("chat"))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

