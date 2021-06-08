import os

from flask import Flask, request, session
from flask_session import Session
from flask_socketio import SocketIO, join_room, leave_room
import mysql.connector

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

Session(app)


def delete_player_from_room():
    print("[ROOM #" + str(session['room']) + "] Started deleting " + str(session['username']) + " from room...")

    mydb = getConnection()
    mycursor = mydb.cursor(buffered=True)

    mycursor.execute("SELECT id, password FROM users WHERE nick=%s", (session['username'],))

    playerID = mycursor.fetchone()
    password = None

    if playerID is not None:
        if isinstance(playerID, tuple):
            playerID, password = playerID

        mydb.commit()
        mycursor.close()
        mydb.close()

        mydb = getConnection()
        mycursor = mydb.cursor(buffered=True)

        mycursor.execute("SELECT players FROM servers WHERE idServer = %s", (session['room'],))

        playersS = mycursor.fetchone()

        if playersS is not None:
            if isinstance(playersS, tuple):
                playersS = playersS[0]

            playersArray = playersS.split(",")
            playersArray.remove(str(playerID))

            mydb.commit()
            mycursor.close()
            mydb.close()

            mydb = getConnection()
            mycursor = mydb.cursor(buffered=True)

            if len(playersArray) == 0:
                mycursor.execute("DELETE FROM servers WHERE idServer = %s", (int(session['room']),))

                mydb.commit()
                mycursor.close()
                mydb.close()

            else:
                newPlayers = ','.join(playersArray)
                mycursor.execute("UPDATE servers SET players = %s WHERE idServer = %s",
                                 (newPlayers, int(session['room'])))

                mydb.commit()
                mycursor.close()
                mydb.close()

            if password is None:
                mydb = getConnection()
                mycursor = mydb.cursor(buffered=True)

                mycursor.execute("DELETE FROM users WHERE id = %s", (int(playerID),))

                mydb.commit()
                mycursor.close()
                mydb.close()

                print("[ROOM #" + str(session['room']) + "] Successfully deleted guest " + str(
                    session['username']) + " from database!")

            print(
                "[ROOM #" + str(session['room']) + "] Successfully deleted " + str(session['username']) + " from room!")

    print("[ROOM #" + str(session['room']) + "] " + str(session['username']) + " left")


def add_player_to_room(data):
    nick = data['nick']
    room = data['roomId']
    session['username'] = nick
    session['room'] = room
    session['ssid'] = request.sid
    join_room(data['roomId'])

    print("[ROOM #" + str(room) + "] Started adding " + str(nick) + " to room...")

    mydb = getConnection()
    mycursor = mydb.cursor(buffered=True)

    mycursor.execute("SELECT id FROM users WHERE nick=%s", (session['username'],))

    playerID = mycursor.fetchone()

    if playerID is not None:
        if isinstance(playerID, tuple):
            playerID = playerID[0]

        session['id'] = playerID

        mydb.commit()
        mycursor.close()
        mydb.close()

        mydb = getConnection()
        mycursor = mydb.cursor(buffered=True)

        mycursor.execute("SELECT players FROM servers WHERE idServer = %s", (session['room'],))

        playersS = mycursor.fetchone()

        if playersS is not None:
            if isinstance(playersS, tuple):
                playersS = playersS[0]

            playersArray = playersS.split(",")

            mydb.commit()
            mycursor.close()
            mydb.close()

            mydb = getConnection()
            mycursor = mydb.cursor(buffered=True)

            if str(playerID) not in playersArray:
                newPlayers = ','.join(playersArray) + ',' + str(playerID)
                mycursor.execute("UPDATE servers SET players = %s WHERE idServer = %s", (newPlayers, int(room)))

                print("[ROOM #" + str(room) + "] Successfully added " + str(nick) + " to room!")
            else:
                print("[ROOM #" + str(room) + "]" + str(nick) + " is already in the room")

            mydb.commit()
            mycursor.close()
            mydb.close()

    print("[ROOM #" + str(session['room']) + "] " + str(session['username']) + " joined")


def getConnection():
    mydb = mysql.connector.connect(
        host=".com",
        user="",
        passwd="",
        database="",
        port=0)

    return mydb


def get_colors_from_players(data):
    socketio.emit('get session', room=data['roomId'])


@socketio.on('sent back session')
def got_session():
    if 'color' in session.keys():
        color = session['color']
    else:
        color = None
    room = session['room']
    nick = session['username']
    socketio.emit('set colors', {"color": color, "nick": nick}, room=room)

    mydb = getConnection()
    mycursor = mydb.cursor(buffered=True)
    mycursor.execute(
        "SELECT r.nazwa_klasy FROM rangi r, user_info ui, users u WHERE u.nick = %s AND u.id = ui.id_user AND ui.elo BETWEEN r.min AND r.max",
        (nick,))
    klasa = mycursor.fetchone()[0]
    mydb.commit()
    mycursor.close()
    mydb.close()

    socketio.emit('send back klase', {"klasa": klasa, "nick": nick}, room=room)


@app.route("/")
def hello():
    return "Hello world"


@socketio.on('join room')
def room_join(json):
    data = json
    nick = data['nick']
    room = data['roomId']
    data['color'] = None
    add_player_to_room(data)
    get_colors_from_players(data)

    socketio.emit('user leave_join', {"msg": "<p class='greenMsg'><b>" + nick + " joined the room.</b></p>"}, room=room)


@socketio.on('disconnect')
def check_dc():
    delete_player_from_room()
    if 'color' in session:
        if session['color'] is not None:
            socketio.emit('delete color', {"color": session['color']}, room=session['room'])

    socketio.emit('message', "Opuścił: " + str(session['username']) + ' pokój numer ' + str(session['room']),
                  room=session['room'])
    if 'color' not in session:
        session['color'] = None
    data = {"roomId": session['room'], "nick": session['username'], "color": session['color']}
    socketio.emit('client left', data, room=session['room'])
    socketio.emit('user leave_join', {"msg": "<p class='redMsg'><b>" + session['username'] + " left the room.</b></p>"},
                  room=session['room'])
    leave_room(session['room'])
    session.clear()


@socketio.on('send pionki na mecie')
def send_pionki_na_mecie(data):
    color = data['color']
    pionki_na_mecie = data['pionki_na_mecie']
    nick = session['username']
    room = session['room']
    socketio.emit('receive pionki na mecie', {"color": color, "pionki_na_mecie": pionki_na_mecie, "nick": nick},
                  room=room)


@socketio.on('send player end')
def send_player_end(data):
    room = session['room']
    color = data['color']
    nick = session['username']
    socketio.emit('receive player end', {"color": color, "nick": nick}, room=room)


@socketio.on('send info')
def send_info(data):
    room = session['room']
    msg = data['msg']
    socketio.emit('get info', {"msg": msg}, room=room)


@socketio.on('end game')
def end_game(data):
    room = session['room']
    socketio.emit('send end game', data, room=room)


@socketio.on('get dice')
def get_dice(data):
    room = session['room']
    dice = data['dice']
    socketio.emit('set dice', {"dice": dice}, room=room)


@socketio.on('start game')
def start_game(data):
    room = session['room']
    firstPlayer = data['firstPlayer']
    print("[ROOM #" + str(room) + "] Game started, first player number #" + str(firstPlayer))
    socketio.emit('game started', {"firstPlayer": firstPlayer}, room=room)


@socketio.on('pre start game')
def pre_start_game(data):
    room = session['room']
    firstPlayer = data['firstPlayer']
    socketio.emit('pre game sessions', {"firstPlayer": firstPlayer}, room=room)


@socketio.on('ruch pionka')
def ruch_pionka(data):
    room = session['room']
    color = data['color']
    ruch = data['ruch']
    socketio.emit('send ruch pionka', data, room=room)


@socketio.on('zbity pionek')
def zbity_pionek(data):
    room = session['room']
    color = session['color']
    zbity_pion = data['zbity_pionek']
    kolor_sprawdzany = data['kolor_bazy']
    socketio.emit('send zbity pionek',
                  {"zbity_pionek": zbity_pion, "kolor_bazy": kolor_sprawdzany, "ruch": data['ruch']}, room=room)


@socketio.on('nastepny gracz')
def nastepny_gracz(data):
    color = data['color']
    room = session['room']
    socketio.emit('send nastepny gracz', {"color": color}, room=room)


@socketio.on('send message')
def got_message(data):
    room = session['room']
    msg = data['msg']
    nick = session['username']
    socketio.emit('receive message', {"msg": msg, "nick": nick}, room=room)


@socketio.on("join as color")
def join_as_color(data):
    nick = data['nick']
    room = data['roomId']
    color = data['color']
    session['color'] = color
    print("[ROOM #" + str(room) + "] " + str(nick) + " chose color " + str(color))
    socketio.emit('color choose', data, room=room)


@socketio.on('message')
def message(json):
    data = json
    msg = data['msg']
    room = data['roomId']
    nick = data['nick']
    message = "<b>" + str(nick) + ":</b> " + str(msg)
    socketio.emit("message", message, room=room)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 2077))
    host = os.environ.get('HOST', "0.0.0.0")
    print("[ROOT] Server started at", str(host) + ":" + str(port))
    socketio.run(app, port=port, host=host)