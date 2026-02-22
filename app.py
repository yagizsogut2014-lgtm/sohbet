import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev_key_123_karizma'

# VERCEL İÇİN KRİTİK AYAR: 
# Eğer Vercel'deysen dosyaya yazamazsın, o yüzden hafızada (RAM) çalıştırıyoruz.
# Localdeysen 'sqlite:///database.db' yapabilirsin ama Vercel hatasını bu çözer.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# Vercel serverless olduğu için WebSocket'i tam desteklemez ama bu ayarlar en stabil halidir
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    friends = db.Column(db.String(500), default="")

online_users = {}

# Veritabanını her başlangıçta temiz oluşturur
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    if 'user' in session:
        user_obj = User.query.filter_by(username=session['user']).first()
        if not user_obj: # Session var ama DB sıfırlanmışsa (Vercel restart)
            session.clear()
            return redirect(url_for('login'))
        f_list = user_obj.friends.split(',') if user_obj.friends and user_obj.friends.strip() else []
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
            session.permanent = True
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/add_friend', methods=['POST'])
def add_friend():
    if 'user' not in session: return jsonify({"success": False})
    data = request.json
    friend_name = data.get('friend_name', '').strip()
    me = User.query.filter_by(username=session['user']).first()
    target = User.query.filter_by(username=friend_name).first()

    if target and friend_name != me.username:
        current_friends = me.friends.split(',') if me.friends else []
        if friend_name not in current_friends:
            current_friends.append(friend_name)
            me.friends = ",".join(filter(None, current_friends))
            db.session.commit()
            return jsonify({"success": True})
    return jsonify({"success": False, "error": "Kullanıcı bulunamadı veya zaten ekli!"})

@socketio.on('connect')
def connect():
    if 'user' in session:
        online_users[session['user']] = request.sid

@socketio.on('private_message')
def handle_msg(data):
    recipient = data['to']
    msg = data['message']
    sender = session.get('user')
    if recipient in online_users:
        emit('new_private_msg', {'from': sender, 'msg': msg}, room=online_users[recipient])
    emit('new_private_msg', {'from': sender, 'msg': msg}, room=request.sid)

# Vercel'in uygulamayı görebilmesi için 'app' nesnesini globalde bırakıyoruz
if __name__ == '__main__':
    socketio.run(app, debug=True)
