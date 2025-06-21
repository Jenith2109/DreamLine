from flask import Flask, request, render_template, redirect, url_for, session, jsonify
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

app = Flask(__name__)
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
    return redirect('/')

@app.route("/", methods=["GET", "POST"])
def chat():
    if "user" not in session:
        return render_template("landing.html")

    user_info = session["user"]
    username = user_info.get('name', 'User')
    user_id = get_or_create_user(username)

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
            memory = get_memory(user_id)
            response = generate_response(user_input, memory)
            save_message(user_id, f"AI: {response}")
            return jsonify({'response': response})
        
        return jsonify({'response': 'No input provided.'}), 400

    # For GET requests, render the full page with chat history
    memory = get_memory(user_id)
    return render_template("chat.html", username=username, memory=memory)

@app.route("/new_chat", methods=["POST"])
def new_chat():
    if "user" not in session:
        return redirect(url_for("login"))
    
    user_info = session.get("user")
    if not user_info:
        return redirect(url_for("login"))

    username = user_info.get("name", "User")
    user_id = get_or_create_user(username)
    # Clear all messages for this user
    conn = sqlite3.connect('dip_users.db')
    c = conn.cursor()
    c.execute('DELETE FROM memories WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("chat"))

