import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit
from supabase import create_client, Client

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev_key_777'

# --- SUPABASE BAĞLANTISI ---
# Buradaki URL'yi Supabase panelinden (Settings > API) bulup değiştir knk
SUPABASE_URL = "BURAYA_SUPABASE_URL_GELCEK" 
SUPABASE_KEY = "sb_publishable_tcqc87q-qe_isAjASnVZLA_amjRZqLv"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Vercel için socketio ayarı
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
online_users = {}

@app.route('/')
def home():
    if 'user' in session:
        try:
            res = supabase.table('users').select('friends').eq('username', session['user']).execute()
            f_list = []
            if res.data and res.data[0].get('friends'):
                f_list = res.data[0]['friends'].split(',')
            return render_template('index.html', user=session['user'], friends=f_list)
        except:
            session.clear()
            return redirect(url_for('login'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        if username:
            # Kullanıcıyı bul veya oluştur
            res = supabase.table('users').select('*').eq('username', username).execute()
            if not res.data:
                supabase.table('users').insert({"username": username, "friends": ""}).execute()
            session['user'] = username
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/add_friend', methods=['POST'])
def add_friend():
    friend_name = request.json.get('friend_name', '').strip()
    me_name = session.get('user')
    if not me_name: return jsonify({"success": False})

    target = supabase.table('users').select('*').eq('username', friend_name).execute()
    if target.data and friend_name != me_name:
        me_data = supabase.table('users').select('friends').eq('username', me_name).execute()
        current_friends = me_data.data[0]['friends'].split(',') if me_data.data[0]['friends'] else []
        if friend_name not in current_friends:
            current_friends.append(friend_name)
            new_list = ",".join(filter(None, current_friends))
            supabase.table('users').update({"friends": new_list}).eq('username', me_name).execute()
            return jsonify({"success": True})
    return jsonify({"success": False, "error": "Kullanıcı bulunamadı!"})

@socketio.on('connect')
def connect():
    if 'user' in session: online_users[session['user']] = request.sid

@socketio.on('private_message')
def handle_msg(data):
    recipient = data['to']
    sender = session.get('user')
    if recipient in online_users:
        emit('new_private_msg', {'from': sender, 'msg': data['message']}, room=online_users[recipient])
    emit('new_private_msg', {'from': sender, 'msg': data['message']}, room=request.sid)

if __name__ == '__main__':
    socketio.run(app, debug=True)
