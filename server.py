import logging
import random
from collections import defaultdict

from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect

import avalon as avalon
import model as m
import rules as r

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
logging.basicConfig(filename='server.log',level=logging.DEBUG)
pids = set()
pid_to_name = defaultdict(unicode)
name_to_pid = defaultdict(unicode)
game = avalon.Game(lambda a,b: a)
votes = {}

def display(msg):
    emit('log', { 'msg': msg }, broadcast=True)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('request_pid')
def request_pid():
    pid = str(random.getrandbits(64))
    pids.add(pid)
    emit('set_pid', {'pid': pid})

@socketio.on('submit')
def submit(data):
    msg = data['msg']
    logging.debug(msg)
    process(str(data['pid']), msg)

def process(pid, msg):
    command, _, arg = msg.partition(u' ')
    if command == u'/start':
        display(u'The game has started. Players:')
        map(lambda p: display(pid_to_name[p]), pids)
        game.add_players(list(pids))

    if command == u'/msg':
        display(arg)

    if command == u'/name':
        pid_to_name[pid] = arg
        name_to_pid[arg] = pid
        display(u'New player: {}'.format(arg))

    elif command == u'/nominate':
        names = arg.split()
        display(u'Nominated: ' + ' '.join(names))
        if (game.status is m.GameStatus.nominating_team and
            pid == game.leader):
            game.nominate_team([name_to_pid[n] for n in names])

    elif command == u'/vote':
        if arg == u'yes':
            votes[pid] = m.Vote.yes
        elif arg == u'no':
            votes[pid] = m.Vote.no
        else:
            return
        display(pid_to_name[pid] + ' has voted.')

        if game.status is m.GameStatus.voting_for_team:
            game.vote_for_team(map(lambda p: r.PlayerVote(p, votes[pid]), votes))
        elif game.status is m.GameStatus.voting_for_mission:
            game.vote_for_mission(map(lambda p: r.PlayerVote(p, votes[pid]), votes))

    elif command == u'/guess':
        name = arg.strip()
        display(u'Guessing {} is Merlin'.format(name))
        game.guess_merlin(name_to_pid[arg])

    display('Currently: ' + game.status)
    if game.leader:
        display('Leader is: ' + pid_to_name[game.leader])
    if game.winner:
        display('Winner is: ' + game.winner)

if __name__ == '__main__':
    socketio.run(app, debug=True)
