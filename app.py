import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sohbet_gizli_anahtar_99'

# --- SUPABASE POSTGRES BAGLANTISI ---
# Buradaki [YOUR-PASSWORD] yerine Supabase giris sifreni yaz knk!
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:[YOUR-PASSWORD]@db.axyoasmvguxvcsxutsng.supabase.co:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# Vercel'de en stabil calisan socket modu
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    friends = db.Column(db.Text, default="")

# Tabloyu otomatik olusturur
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    if 'user' in session:
        user_obj = User.query.filter_by(username=session['user']).first()
        f_list = user_obj.friends.split(',') if user_obj and user_obj.friends else []
        return render_template('index.html', user=session['user'], friends=f_list)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        if username:
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username)
                db.session.add(user)
                db.session.commit()
            session['user'] = username
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/add_friend', methods=['POST'])
def add_friend():
    data = request.json
    friend_name = data.get('friend_name', '').strip()
    me = User.query.filter_by(username=session['user']).first()
    target = User.query.filter_by(username=friend_name).first()

    if target and me and friend_name != me.username:
        friends = me.friends.split(',') if me.friends else []
        if friend_name not in friends:
            friends.append(friend_name)
            me.friends = ",".join(filter(None, friends))
            db.session.commit()
            return jsonify({"success": True})
    return jsonify({"success": False, "error": "Kullanici bulunamadi!"})

@socketio.on('connect')
def connect():
    pass

@socketio.on('private_message')
def handle_msg(data):
    # Basit bir mesaj gonderme mantigi
    emit('new_private_msg', {'from': session.get('user'), 'msg': data['message']}, broadcast=True)

# Vercel icin app'i disari veriyoruz
app = app

if __name__ == '__main__':
    socketio.run(app, debug=True)
