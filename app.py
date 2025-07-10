from flask import Flask, render_template, request, redirect, url_for, session, Response
from datetime import datetime, timedelta
import uuid
import calendar

app = Flask(__name__)
app.secret_key = 'super-secret-key-123'

# Имитация базы данных
users_db = {}
events_db = {}
user_events_db = {}

def get_user_events(username):
    events = {}
    for event_id in user_events_db.get(username, []):
        event = events_db.get(event_id)
        if event:
            date = event['date']
            if date not in events:
                events[date] = []
            events[date].append(event)
    return events

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('calendar_view'))
    return render_template('home.html', dark_mode=session.get('dark_mode', False))

@app.route('/toggle_theme')
def toggle_theme():
    session['dark_mode'] = not session.get('dark_mode', False)
    return redirect(request.referrer or url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users_db:
            return render_template('error.html', message="Пользователь уже существует", dark_mode=session.get('dark_mode', False))
        users_db[username] = password
        return redirect(url_for('login'))
    return render_template('register.html', dark_mode=session.get('dark_mode', False))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username not in users_db or users_db[username] != password:
            return render_template('error.html', message="Неверное имя пользователя или пароль", dark_mode=session.get('dark_mode', False))
        session['username'] = username
        return redirect(url_for('calendar_view'))
    return render_template('login.html', dark_mode=session.get('dark_mode', False))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/add_event', methods=['POST'])
def add_event():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    event_id = str(uuid.uuid4())
    title = request.form['title']
    date = request.form['date']
    time = request.form.get('time', '')
    description = request.form.get('description', '')

    event = {
        'id': event_id,
        'title': title,
        'date': date,
        'time': time,
        'description': description
    }

    events_db[event_id] = event
    if username not in user_events_db:
        user_events_db[username] = []
    user_events_db[username].append(event_id)

    return redirect(url_for('calendar_view'))

@app.route('/export/<event_id>')
def export_event(event_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    if event_id not in events_db or event_id not in user_events_db.get(username, []):
        return render_template('error.html', message="Событие не найдено", dark_mode=session.get('dark_mode', False))

    event = events_db[event_id]
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:{event_id}
DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}
DTSTART:{event['date'].replace('-', '')}
SUMMARY:{event['title']}
DESCRIPTION:{event['description']}
END:VEVENT
END:VCALENDAR"""

    return Response(
        ics_content,
        mimetype='text/calendar',
        headers={'Content-Disposition': f'attachment; filename=event_{event_id}.ics'}
    )

@app.route('/calendar')
def calendar_view():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']

    if 'delete' in request.args:
        event_id = request.args.get('delete')
        if event_id in events_db and event_id in user_events_db.get(username, []):
            del events_db[event_id]
            user_events_db[username] = [eid for eid in user_events_db[username] if eid != event_id]

    today = datetime.today()
    year = request.args.get('year', type=int, default=today.year)
    month = request.args.get('month', type=int, default=today.month)

    if month > 12:
        year += 1
        month = 1
    elif month < 1:
        year -= 1
        month = 12

    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]

    user_events = get_user_events(username)

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    events_list = []
    for date_str, events in sorted(user_events.items(), reverse=True):
        for event in events:
            events_list.append(event)

    return render_template('calendar.html',
                           username=username,
                           year=year,
                           month=month,
                           month_name=month_name,
                           prev_year=prev_year,
                           prev_month=prev_month,
                           next_year=next_year,
                           next_month=next_month,
                           cal=cal,
                           today=today,
                           user_events=user_events,
                           events_list=events_list,
                           dark_mode=session.get('dark_mode', False)
                           )

@app.route('/get_events/<date>')
def get_events(date):
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    events = []
    for event_id in user_events_db.get(username, []):
        event = events_db.get(event_id)
        if event and event['date'] == date:
            events.append(event)

    return render_template('events_modal.html', events=events, date=date, dark_mode=session.get('dark_mode', False))

if __name__ == '__main__':
    app.run(debug=True)