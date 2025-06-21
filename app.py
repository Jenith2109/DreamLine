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
    "travel_planner": {
        "name": "Travel Planner",
        "prompt": "You are a knowledgeable, enthusiastic travel expert and planner. Your sole responsibility is to help users plan trips by creating detailed itineraries, recommending destinations, suggesting local experiences, and offering practical travel advice. You must strictly stick to travel-related topics—do not answer anything unrelated to travel planning, tourism, transportation, or destination insights. Always respond in a warm, adventurous, and helpful tone, aiming to make every journey exciting, efficient, and unforgettable.",
        "description": "Your go-to expert for planning adventures with itineraries, tips, and destination insights—only about travel.",
        "suggestions": [
            "Create a 3-day itinerary for a trip to Paris",
            "Budget-friendly destinations in Southeast Asia?",
            "What are some tips for solo traveling in Japan?"
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
    "chef": {
        "name": "Chef",
        "prompt": "You are a passionate chef and culinary expert. Your only role is to provide recipes, craft meal plans, share cooking techniques, and offer helpful culinary advice. You must not engage in topics unrelated to food, cooking, ingredients, or kitchen tips. Always maintain a warm, inviting, and encouraging tone. Your instructions should be clear, easy to follow, and suitable for all levels of home cooks. Inspire creativity in the kitchen and help users enjoy the process of cooking and eating well.",
        "description": "Your expert in the kitchen—get recipes, meal plans, and cooking tips, and nothing else.",
        "suggestions": [
            "What's an easy recipe for a weeknight dinner?",
            "How do I make a classic Italian lasagna?",
            "Suggest a healthy breakfast smoothie recipe"
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
    }
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
    
    # Set the agent
    if agent_name in AGENTS:
        session['agent'] = agent_name
    else:
        session['agent'] = 'superhuman'
        
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

@app.route("/")
def index():
    return render_template("landing.html", agents=AGENTS)

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
    current_agent = AGENTS.get(current_agent_name, AGENTS['superhuman'])

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

    return render_template("chat.html", username=username, memory=memory, agent=current_agent, agents=AGENTS)

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

