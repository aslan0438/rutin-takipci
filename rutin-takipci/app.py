from flask import Flask, render_template, request, redirect, url_for
import json
import os
from datetime import date, timedelta

app = Flask(__name__)
DATA_FILE = 'data.json'

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"habits": [], "logs": {}}
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

def get_streak(habit, logs):
    streak = 0
    check_date = date.today()
    while True:
        day_str = str(check_date)
        if day_str in logs and habit in logs[day_str]:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    return streak

@app.route('/')
def index():
    data = load_data()
    today = str(date.today())
    streaks = {habit: get_streak(habit, data['logs']) for habit in data['habits']}
    total = len(data['habits'])
    completed_today = len([h for h in data['habits'] if today in data['logs'] and h in data['logs'][today]])
    percent = int((completed_today / total) * 100) if total > 0 else 0
    return render_template('index.html', habits=data['habits'], logs=data['logs'], today=today, streaks=streaks, percent=percent, completed=completed_today, total=total)

@app.route('/add', methods=['POST'])
def add_habit():
    data = load_data()
    habit = request.form.get('habit')
    if habit and habit not in data['habits']:
        data['habits'].append(habit)
        save_data(data)
    return redirect(url_for('index'))

@app.route('/complete/<habit>')
def complete(habit):
    data = load_data()
    today = str(date.today())
    if today not in data['logs']:
        data['logs'][today] = []
    if habit not in data['logs'][today]:
        data['logs'][today].append(habit)
    save_data(data)
    return redirect(url_for('index'))

@app.route('/delete/<habit>')
def delete(habit):
    data = load_data()
    data['habits'] = [h for h in data['habits'] if h != habit]
    for day in data['logs']:
        if habit in data['logs'][day]:
            data['logs'][day].remove(habit)
    save_data(data)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)