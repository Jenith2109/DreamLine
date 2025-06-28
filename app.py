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
    "superhuman": {
        "name": "SuperHuman",
        "prompt": "You are SuperHuman—an advanced, intelligent, and futuristic AI assistant. Your purpose is to help users with a wide variety of tasks including answering questions, solving problems, offering recommendations, organizing information, and providing insights across domains such as productivity, technology, creativity, wellness, and more. You must always be friendly, adaptive, and responsive, delivering answers in a clear, thoughtful, and human-like tone. Behave like the perfect blend of human intuition and AI precision. Always aim to impress with usefulness, clarity, and a touch of futuristic charm. You are the ultimate partner for users seeking smart, seamless support in their daily lives and big goals.",
        "description": "Your intelligent, futuristic, and friendly partner for everything—from daily tasks to big ideas.",
        "suggestions": [
            "Explain quantum computing in simple terms",
            "Got any creative ideas for a 10 year old's birthday?",
            "How do I make an HTTP request in Javascript?"
        ]
    },
    "creative_writer": {
        "name": "Creative Writer",
        "prompt": "You are a master storyteller, poet, and creative writer. Your sole purpose is to craft and assist with imaginative writing—stories, poems, narratives, and evocative marketing copy. You must **only** engage in topics related to creative expression through writing. Do not respond to questions outside the realms of storytelling, poetry, creative fiction/nonfiction, or marketing content. Always write with a vivid, expressive, and artistic tone. You are here to inspire and create wonder through words, bringing ideas to life with flair and emotion.",
        "description": "Your dedicated partner for stories, poems, and marketing copy. You speak only in the language of creativity.",
        "suggestions": [
            "Write a short poem about the moon",
            "Draft a catchy slogan for a coffee shop",
            "Help me start a fantasy story"
        ]
    },
    "code_assistant": {
        "name": "Code Assistant",
        "prompt": "You are an expert programmer and technical code assistant. Your exclusive role is to help users write, debug, optimize, and understand code across various languages and frameworks. You must strictly focus on coding, programming concepts, software development, and debugging tasks. Avoid discussing any topic outside the realm of code and development. Always provide clear, concise explanations, formatted code snippets using markdown syntax, and best practices when relevant. Think like a senior developer helping a peer—precise, focused, and efficient.",
        "description": "Your expert guide for writing, debugging, and understanding code—nothing else.",
        "suggestions": [
            "How to implement a binary search in Python?",
            "Explain the concept of recursion",
            "SQL vs. NoSQL: What are the differences?"
        ]
    },
    "career_coach": {
        "name": "Career Coach",
        "prompt": "You are a supportive and insightful career coach. Your exclusive role is to help users with resume writing, interview preparation, job search strategies, and career development. You must only engage in topics directly related to professional growth, career planning, and workplace success. Avoid responding to unrelated questions. Always maintain an encouraging, practical, and goal-oriented tone. Provide clear, actionable advice tailored to each user's professional journey, whether they're starting out or seeking advancement.",
        "description": "Your trusted guide for resumes, interviews, job search strategies, and career growth—nothing else.",
        "suggestions": [
            "Review my resume for a software engineer role",
            "How should I prepare for a behavioral interview?",
            "What are some high-demand skills to learn in 2025?"
        ]
    },
    "fitness_trainer": {
        "name": "Fitness Trainer",
        "prompt": "You are a certified fitness trainer and health motivator. Your sole focus is to create personalized workout plans, provide fitness and exercise advice, and encourage users to reach their health and physical goals. Do not respond to topics outside fitness, exercise science, health routines, or wellness motivation. Always maintain an energetic, knowledgeable, and supportive tone. Your guidance should be practical, safe, and suitable for users of all fitness levels—from beginners to advanced athletes.",
        "description": "Your energetic expert for fitness advice, custom workouts, and health motivation—only fitness, nothing else.",
        "suggestions": [
            "Create a 30-minute HIIT workout for me",
            "What are some good exercises to strengthen my core?",
            "How can I improve my running stamina?"
        ]
    },
    "adaptive_agent": {
        "name": "Adaptive Agent",
        "prompt": "You are an Adaptive AI, a master of personas. Your primary function is to adopt any role the user assigns to you at any point in the conversation. Analyze each user message for instructions to change your persona (e.g., 'Now, act as a pirate,' or 'Become a world-class chef.'). When you receive such a command, you must immediately adopt the new role and maintain it consistently until you are given new instructions. If a user message does not contain instructions to change your persona, continue with your current role. If no role has been assigned at the start of a conversation, act as a helpful, general-purpose assistant and await direction.",
        "description": "A chameleon AI. Define its role with your first message and it will adapt to your needs.",
        "suggestions": [
            "You are a stand-up comedian. Tell me a joke.",
            "Let's have a debate. You argue for and I'll argue against.",
            "Become a travel guide for ancient Rome."
        ]
    }
}

DYNAMIC_AGENTS = AGENTS.copy()
DYNAMIC_AGENTS['custom'] = {
    "name": "Custom Agent",
    "description": "Create your own specialist agent with a unique personality and purpose.",
    "prompt": "", 
    "suggestions": [
        "What can you do?",
        "How do I customize you?",
        "Tell me a joke."
    ]
}

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')

# --- SERVER-SIDE SESSION CONFIGURATION ---
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_DIR'] = './flask_session'
Session(app)

# --- OAUTH CONFIGURATION ---
app.config.from_mapping(
    GOOGLE_CLIENT_ID=os.environ.get("GOOGLE_CLIENT_ID"),
    GOOGLE_CLIENT_SECRET=os.environ.get("GOOGLE_CLIENT_SECRET"),
)
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
    
    user_id = get_or_create_user(session["user"].get("name", "User"))

    if agent_name == 'custom':
        conn = sqlite3.connect('dip_users.db')
        c = conn.cursor()
        c.execute("SELECT custom_prompt FROM users WHERE id = ?", (user_id,))
        user_prompt = c.fetchone()
        conn.close()
        if not user_prompt or not user_prompt[0]:
            return redirect(url_for('custom_agent'))

    if agent_name in DYNAMIC_AGENTS:
        session['agent'] = agent_name
    else:
        session['agent'] = 'superhuman'
        
    conn = sqlite3.connect('dip_users.db')
    c = conn.cursor()
    c.execute('DELETE FROM memories WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('chat'))

@app.route("/")
def index():
    # Get user's custom agents if logged in
    custom_agents = {}
    if "user" in session:
        user_id = get_or_create_user(session["user"].get("name", "User"))
        conn = sqlite3.connect('dip_users.db')
        c = conn.cursor()
        c.execute("SELECT custom_agent_name, custom_prompt FROM users WHERE id = ?", (user_id,))
        custom_agent_data = c.fetchone()
        conn.close()
        
        if custom_agent_data and custom_agent_data[0] and custom_agent_data[1]:
            custom_agents['user_custom'] = {
                "name": custom_agent_data[0],
                "description": "Your personalized AI agent with custom personality and expertise.",
                "prompt": custom_agent_data[1],
                "suggestions": [
                    "What can you help me with?",
                    "Tell me about your personality",
                    "How were you created?"
                ]
            }
    
    # Combine predefined agents with user's custom agents
    all_agents = DYNAMIC_AGENTS.copy()
    all_agents.update(custom_agents)
    
    return render_template("landing.html", agents=all_agents)

@app.route("/custom-agent", methods=["GET", "POST"])
def custom_agent():
    if "user" not in session:
        return redirect(url_for("login"))

    user_id = get_or_create_user(session["user"].get("name", "User"))
    conn = sqlite3.connect('dip_users.db')
    c = conn.cursor()

    if request.method == "POST":
        agent_name = request.form.get("agent_name", "Custom Agent")
        agent_prompt = request.form.get("agent_prompt", "")
        c.execute("UPDATE users SET custom_agent_name = ?, custom_prompt = ? WHERE id = ?", (agent_name, agent_prompt, user_id))
        conn.commit()
        conn.close()
        return redirect(url_for('set_agent', agent_name='custom'))

    c.execute("SELECT custom_agent_name, custom_prompt FROM users WHERE id = ?", (user_id,))
    custom_agent_data = c.fetchone()
    conn.close()
    
    agent_name = custom_agent_data[0] if custom_agent_data and custom_agent_data[0] else ""
    agent_prompt = custom_agent_data[1] if custom_agent_data and custom_agent_data[1] else ""
    
    return render_template("custom_agent.html", agent_name=agent_name, agent_prompt=agent_prompt)

@app.route("/edit-custom-agent", methods=["GET", "POST"])
def edit_custom_agent():
    if "user" not in session:
        return redirect(url_for("login"))

    user_id = get_or_create_user(session["user"].get("name", "User"))
    conn = sqlite3.connect('dip_users.db')
    c = conn.cursor()

    if request.method == "POST":
        agent_name = request.form.get("agent_name", "Custom Agent")
        agent_prompt = request.form.get("agent_prompt", "")
        c.execute("UPDATE users SET custom_agent_name = ?, custom_prompt = ? WHERE id = ?", (agent_name, agent_prompt, user_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    c.execute("SELECT custom_agent_name, custom_prompt FROM users WHERE id = ?", (user_id,))
    custom_agent_data = c.fetchone()
    conn.close()
    
    if not custom_agent_data or not custom_agent_data[0] or not custom_agent_data[1]:
        return redirect(url_for('custom_agent'))
    
    agent_name = custom_agent_data[0]
    agent_prompt = custom_agent_data[1]
    
    return render_template("edit_custom_agent.html", agent_name=agent_name, agent_prompt=agent_prompt)

@app.route("/remove-custom-agent", methods=["POST"])
def remove_custom_agent():
    if "user" not in session:
        return redirect(url_for("login"))

    user_id = get_or_create_user(session["user"].get("name", "User"))
    conn = sqlite3.connect('dip_users.db')
    c = conn.cursor()
    
    # Clear the custom agent data
    c.execute("UPDATE users SET custom_agent_name = NULL, custom_prompt = NULL WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "user" not in session:
        return redirect(url_for("login"))

    user_info = session["user"]
    username = user_info.get('name', 'User')
    user_id = get_or_create_user(username)
    memory = get_memory(user_id)
    
    # --- Agent Handling ---
    current_agent_name = session.get('agent', 'superhuman')
    
    if current_agent_name == 'custom':
        conn = sqlite3.connect('dip_users.db')
        c = conn.cursor()
        c.execute("SELECT custom_agent_name, custom_prompt FROM users WHERE id = ?", (user_id,))
        custom_agent_data = c.fetchone()
        conn.close()
        
        if not custom_agent_data or not custom_agent_data[1]:
             return redirect(url_for('custom_agent'))
        
        current_agent = {
            "name": custom_agent_data[0] or "Custom Agent",
            "prompt": custom_agent_data[1],
            "suggestions": DYNAMIC_AGENTS['custom']['suggestions']
        }
    else:
        current_agent = DYNAMIC_AGENTS.get(current_agent_name, DYNAMIC_AGENTS['superhuman'])

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
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'memory': memory})

    return render_template("chat.html", username=username, memory=memory, agent=current_agent, agents=DYNAMIC_AGENTS)

@app.route("/new_chat", methods=["POST", "GET"])
def new_chat():
    if "user" not in session:
        return redirect(url_for("login"))
    
    user_info = session.get("user")
    if not user_info:
        return redirect(url_for("login"))

    # New chats from the UI button reset to the superhuman agent
    session['agent'] = 'superhuman'

    username = user_info.get("name", "User")
    user_id = get_or_create_user(username)
    conn = sqlite3.connect('dip_users.db')
    c = conn.cursor()
    c.execute('DELETE FROM memories WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for("chat"))

@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect(url_for("login"))
    user_info = session["user"]
    return render_template("profile.html", user=user_info)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

