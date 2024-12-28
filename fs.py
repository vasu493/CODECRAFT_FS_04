from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO, join_room, leave_room, emit
import os
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

bcrypt = Bcrypt(app)
socketio = SocketIO(app, cors_allowed_origins="*")
db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Chat Room model
class ChatRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

# Message model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=False)

# Routes
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Username and password are required."}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists."}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully."}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"message": "Invalid credentials."}), 401

    return jsonify({"message": "Login successful.", "user_id": user.id}), 200

@app.route('/create_room', methods=['POST'])
def create_room():
    data = request.json
    room_name = data.get('name')

    if not room_name:
        return jsonify({"message": "Room name is required."}), 400

    if ChatRoom.query.filter_by(name=room_name).first():
        return jsonify({"message": "Room already exists."}), 409

    new_room = ChatRoom(name=room_name)
    db.session.add(new_room)
    db.session.commit()

    return jsonify({"message": "Room created successfully."}), 201

# WebSocket Events
@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    emit('message', {'username': 'System', 'content': f'{username} has joined the room.'}, room=room)

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    emit('message', {'username': 'System', 'content': f'{username} has left the room.'}, room=room)

@socketio.on('send_message')
def on_message(data):
    username = data['username']
    room = data['room']
    content = data['content']

    user = User.query.filter_by(username=username).first()
    chat_room = ChatRoom.query.filter_by(name=room).first()

    if user and chat_room:
        new_message = Message(content=content, user_id=user.id, room_id=chat_room.id)
        db.session.add(new_message)
        db.session.commit()

        emit('message', {'username': username, 'content': content}, room=room)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
