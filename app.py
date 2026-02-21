from flask import Flask, render_template, request, redirect, session, flash, jsonify, url_for
import sqlite3
import bcrypt
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Random import get_random_bytes
import base64
import json
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")


# ============ ENCRYPTION FUNCTIONS ============

def encrypt_message(message, recipient_public_key):
    """
    Encrypt message using AES + RSA hybrid encryption
    Returns: {encrypted_aes_key, ciphertext, nonce, tag}
    """
    # Generate random AES key
    aes_key = get_random_bytes(16)
    
    # Encrypt message with AES in EAX mode (authenticated encryption)
    cipher_aes = AES.new(aes_key, AES.MODE_EAX)
    ciphertext, tag = cipher_aes.encrypt_and_digest(message.encode())
    
    # Encrypt AES key with recipient's RSA public key
    public_key = RSA.import_key(recipient_public_key)
    cipher_rsa = PKCS1_OAEP.new(public_key)
    encrypted_aes_key = cipher_rsa.encrypt(aes_key)
    
    return {
        "encrypted_aes_key": base64.b64encode(encrypted_aes_key).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "nonce": base64.b64encode(cipher_aes.nonce).decode(),
        "tag": base64.b64encode(tag).decode()
    }


def decrypt_message(encrypted_data, private_key):
    """
    Decrypt message using private key
    Returns: decrypted message as string
    """
    try:
        # Decode from base64
        encrypted_aes_key = base64.b64decode(encrypted_data["encrypted_aes_key"])
        ciphertext = base64.b64decode(encrypted_data["ciphertext"])
        nonce = base64.b64decode(encrypted_data["nonce"])
        tag = base64.b64decode(encrypted_data["tag"])
        
        # Decrypt AES key with private key
        private_key_obj = RSA.import_key(private_key)
        cipher_rsa = PKCS1_OAEP.new(private_key_obj)
        aes_key = cipher_rsa.decrypt(encrypted_aes_key)
        
        # Decrypt message with AES
        cipher_aes = AES.new(aes_key, AES.MODE_EAX, nonce=nonce)
        message = cipher_aes.decrypt_and_verify(ciphertext, tag)
        
        return message.decode()
    except Exception as e:
        return None


# ---------------- DATABASE INIT ----------------

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Create tables with the expected schema if they don't exist.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        public_key TEXT NOT NULL,
        private_key TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT NOT NULL,
        receiver TEXT NOT NULL,
        encrypted_aes_key TEXT NOT NULL,
        ciphertext TEXT NOT NULL,
        nonce TEXT NOT NULL,
        tag TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Ensure old databases get the new columns if they are missing
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [row[1] for row in cursor.fetchall()]
    if 'private_key' not in user_cols:
        # Add private_key column (nullable) to avoid breaking existing rows
        cursor.execute("ALTER TABLE users ADD COLUMN private_key TEXT")

    cursor.execute("PRAGMA table_info(messages)")
    msg_cols = [row[1] for row in cursor.fetchall()]
    if 'is_read' not in msg_cols:
        cursor.execute("ALTER TABLE messages ADD COLUMN is_read INTEGER DEFAULT 0")
    if 'message_text' not in msg_cols:
        cursor.execute("ALTER TABLE messages ADD COLUMN message_text TEXT")

    conn.commit()
    conn.close()

init_db()


# ---------------- HOME ----------------

@app.route("/")
def home():
    return redirect("/register")


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Validate input
        if len(username) < 3:
            flash("Username must be at least 3 characters long", "error")
            return redirect("/register")
        if len(password) < 6:
            flash("Password must be at least 6 characters long", "error")
            return redirect("/register")

        # Hash password properly and convert to string for DB storage
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        # Generate RSA public key
        key = RSA.generate(2048)
        public_key = key.publickey().export_key().decode()
        private_key = key.export_key().decode()

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, password, public_key, private_key) VALUES (?, ?, ?, ?)",
                (username, hashed, public_key, private_key)
            )
            conn.commit()
            conn.close()
            flash("Registration successful! Please login.", "success")
            return redirect("/login")
        except sqlite3.IntegrityError:
            conn.close()
            flash("Username already exists! Please choose another.", "error")
            return redirect("/register")

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        conn.close()

        # FIXED bcrypt comparison
        if user and bcrypt.checkpw(password.encode(), user[0].encode()):
            session["username"] = username
            return redirect("/chat")
        else:
            return "Invalid username or password"

    return render_template("login.html")


# ---------------- CHAT ----------------

@app.route("/chat")
def chat():
    if "username" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Get all users except current user
    cursor.execute("SELECT username FROM users WHERE username != ?", (session["username"],))
    users = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template("chat.html", users=users, current_user=session["username"])


# -------- MESSAGING API --------

@app.route("/api/messages/<recipient>", methods=["GET"])
def get_messages(recipient):
    """Get all messages between current user and recipient"""
    if "username" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    current_user = session["username"]
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Get current user's private key
    cursor.execute("SELECT private_key FROM users WHERE username=?", (current_user,))
    user_result = cursor.fetchone()
    if not user_result:
        conn.close()
        return jsonify({"error": "User not found"}), 404
    
    private_key = user_result[0]
    
    # Get all messages between the two users
    cursor.execute("""
        SELECT id, sender, receiver, encrypted_aes_key, ciphertext, nonce, tag, timestamp, is_read, message_text
        FROM messages
        WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
        ORDER BY timestamp ASC
    """, (current_user, recipient, recipient, current_user))
    
    messages_db = cursor.fetchall()
    
    # Mark received messages as read
    cursor.execute("""
        UPDATE messages SET is_read=1 
        WHERE receiver=? AND sender=? AND is_read=0
    """, (current_user, recipient))
    conn.commit()
    
    messages = []
    for row in messages_db:
        msg_id, sender, receiver, enc_key, cipher, nonce, tag, timestamp, is_read, message_text = row
        # Use plaintext message if available, otherwise decrypt
        if message_text:
            text = message_text
        else:
            text = decrypt_message({
                "encrypted_aes_key": enc_key,
                "ciphertext": cipher,
                "nonce": nonce,
                "tag": tag
            }, private_key)
        
        messages.append({
            "id": msg_id,
            "sender": sender,
            "receiver": receiver,
            "text": text,
            "timestamp": timestamp,
            "is_read": is_read
        })
    
    conn.close()
    return jsonify(messages)


@app.route("/api/send", methods=["POST"])
def send_message():
    """Send encrypted message"""
    if "username" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json
    sender = session["username"]
    receiver = data.get("receiver")
    message_text = data.get("message")
    
    if not receiver or not message_text:
        return jsonify({"error": "Missing receiver or message"}), 400
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Get recipient's public key
    cursor.execute("SELECT public_key FROM users WHERE username=?", (receiver,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({"error": "Recipient not found"}), 404
    
    recipient_public_key = result[0]
    
    # Encrypt message
    encrypted = encrypt_message(message_text, recipient_public_key)
    
    # Store encrypted message in database along with plaintext
    cursor.execute("""
        INSERT INTO messages (sender, receiver, encrypted_aes_key, ciphertext, nonce, tag, message_text)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (sender, receiver, encrypted["encrypted_aes_key"], encrypted["ciphertext"], 
          encrypted["nonce"], encrypted["tag"], message_text))
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "Message encrypted and sent"})


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)