import os

from flask import Flask, request, session
from flask_session import Session
from flask_socketio import SocketIO
import mysql.connector

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

Session(app)


def get_connection():
    mydb = mysql.connector.connect(
        host="",
        user="",
        passwd="",
        database="",
        port=0)

    return mydb


def get_rank(user_id):
    mydb = get_connection()
    mycursor = mydb.cursor(buffered=True)
    mycursor.execute(
        "SELECT r.nazwa_klasy FROM rangi r, user_info ui WHERE %s = ui.id_user AND ui.elo BETWEEN r.min AND r.max",
        (user_id,))
    ranga = mycursor.fetchone()[0]
    mydb.commit()
    mycursor.close()
    mydb.close()

    return ranga


@socketio.on('get user data')
def add_player_to_session(data):
    nick = data['nick']
    user_id = data['user_id']
    session['nick'] = nick
    session['user_id'] = user_id
    session['ssid'] = request.sid
    socketio.emit('connection established', room = request.sid)
    print(nick + " joined!")


@socketio.on('send message')
def get_message(data):
    msg = data['msg']
    nick = session['nick']
    user_id = session['user_id']
    if not msg.isspace():
        socketio.emit('receive message', {"msg": msg, "nick": nick, "id": user_id, "ranga": get_rank(user_id)})
        print(nick + ": " + msg)


@socketio.on('disconnect')
def clear_data():
    print(session['nick'] + " left!")
    session.clear()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 2078))
    host = os.environ.get('HOST', "0.0.0.0")
    print("[ROOT] Server started at", str(host) + ":" + str(port))
    socketio.run(app, port=port, host=host)
