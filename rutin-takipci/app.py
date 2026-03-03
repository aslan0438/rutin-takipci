from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta
import os

app = Flask(__name__)
app.secret_key = 'rutin-takipci-secret-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rutin.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'landing'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    habits = db.relationship('Habit', backref='user', lazy=True, cascade='all, delete-orphan')

class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='Genel')
    note = db.Column(db.String(300), default='')
    order = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    logs = db.relationship('HabitLog', backref='habit', lazy=True, cascade='all, delete-orphan')

class HabitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_streak(habit):
    streak = 0
    check_date = date.today()
    log_dates = {l.date for l in habit.logs}
    while str(check_date) in log_dates:
        streak += 1
        check_date -= timedelta(days=1)
    return streak

def get_weekly(habit):
    log_dates = {l.date for l in habit.logs}
    result = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        result.append({'day': d.strftime('%a'), 'done': str(d) in log_dates})
    return result

def calc_xp_for_level(level):
    return level * 100

def add_xp(user, amount):
    user.xp += amount
    while user.xp >= calc_xp_for_level(user.level):
        user.xp -= calc_xp_for_level(user.level)
        user.level += 1

@app.route('/landing')
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('landing.html')

@app.route('/')
@login_required
def index():
    today = str(date.today())
    habits = Habit.query.filter_by(user_id=current_user.id).order_by(Habit.order).all()
    today_logs = []
    for h in habits:
        for l in h.logs:
            if l.date == today:
                today_logs.append(h.id)
    streaks = {str(h.id): get_streak(h) for h in habits}
    weekly = {str(h.id): get_weekly(h) for h in habits}
    total = len(habits)
    completed = len([h for h in habits if h.id in today_logs])
    percent = int((completed / total) * 100) if total > 0 else 0
    xp_needed = calc_xp_for_level(current_user.level)
    xp_percent = int((current_user.xp / xp_needed) * 100) if xp_needed > 0 else 0
    return render_template('index.html',
        habits=habits, today=today, today_logs=today_logs,
        streaks=streaks, weekly=weekly,
        total=total, completed=completed, percent=percent,
        user=current_user, xp_needed=xp_needed, xp_percent=xp_percent)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Bu kullanıcı adı alınmış.')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Bu email zaten kayıtlı.')
            return redirect(url_for('register'))
        user = User(username=username, email=email,
                   password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Kullanıcı adı veya şifre hatalı.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing'))

@app.route('/add', methods=['POST'])
@login_required
def add_habit():
    name = request.form.get('habit')
    category = request.form.get('category', 'Genel')
    note = request.form.get('note', '')
    if name and not Habit.query.filter_by(name=name, user_id=current_user.id).first():
        max_order = db.session.query(db.func.max(Habit.order)).filter_by(user_id=current_user.id).scalar() or 0
        habit = Habit(name=name, category=category, note=note, user_id=current_user.id, order=max_order+1)
        db.session.add(habit)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit/<int:habit_id>', methods=['POST'])
@login_required
def edit_habit(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    habit.name = request.form.get('name', habit.name)
    habit.category = request.form.get('category', habit.category)
    habit.note = request.form.get('note', habit.note)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/complete/<int:habit_id>')
@login_required
def complete(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    today = str(date.today())
    existing = HabitLog.query.filter_by(habit_id=habit_id, date=today).first()
    if not existing:
        log = HabitLog(habit_id=habit_id, date=today)
        db.session.add(log)
        add_xp(current_user, 20)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:habit_id>')
@login_required
def delete(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    db.session.delete(habit)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/logs/<int:habit_id>')
@login_required
def get_logs(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    dates = [l.date for l in habit.logs]
    return jsonify({'dates': dates})

@app.route('/reorder', methods=['POST'])
@login_required
def reorder():
    data = request.get_json()
    for item in data:
        habit = Habit.query.filter_by(id=item['id'], user_id=current_user.id).first()
        if habit:
            habit.order = item['order']
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/stats')
@login_required
def stats():
    habits = current_user.habits
    stat_data = []
    for h in habits:
        log_dates = sorted([l.date for l in h.logs], reverse=True)
        stat_data.append({
            'name': h.name,
            'category': h.category,
            'total': len(log_dates),
            'streak': get_streak(h),
            'dates': log_dates[:90]
        })
    return jsonify(stat_data)

@app.route('/weekly-report')
@login_required
def weekly_report():
    habits = current_user.habits
    report = []
    for h in habits:
        log_dates = {l.date for l in h.logs}
        week_data = []
        for i in range(6, -1, -1):
            d = date.today() - timedelta(days=i)
            week_data.append({
                'date': str(d),
                'day': d.strftime('%A'),
                'done': str(d) in log_dates
            })
        completed_count = sum(1 for w in week_data if w['done'])
        report.append({
            'name': h.name,
            'category': h.category,
            'streak': get_streak(h),
            'week': week_data,
            'completed': completed_count,
            'percent': int((completed_count / 7) * 100)
        })
    return jsonify({
        'username': current_user.username,
        'level': current_user.level,
        'xp': current_user.xp,
        'report': report,
        'week_start': str(date.today() - timedelta(days=6)),
        'week_end': str(date.today())
    })

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        new_username = request.form.get('username')
        new_email = request.form.get('email')
        new_password = request.form.get('password')
        if new_username and new_username != current_user.username:
            if User.query.filter_by(username=new_username).first():
                flash('Bu kullanıcı adı alınmış.')
                return redirect(url_for('profile'))
            current_user.username = new_username
        if new_email and new_email != current_user.email:
            if User.query.filter_by(email=new_email).first():
                flash('Bu email zaten kayıtlı.')
                return redirect(url_for('profile'))
            current_user.email = new_email
        if new_password and len(new_password) >= 6:
            current_user.password = generate_password_hash(new_password)
        db.session.commit()
        flash('Profil güncellendi!')
        return redirect(url_for('profile'))
    total_logs = sum(len(h.logs) for h in current_user.habits)
    max_streak = max((get_streak(h) for h in current_user.habits), default=0)
    return render_template('profile.html', user=current_user, total_logs=total_logs, max_streak=max_streak)

@app.route('/ai-suggest', methods=['POST'])
@login_required
def ai_suggest():
    try:
        import anthropic
        habits = [h.name for h in current_user.habits]
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": f"Kullanıcının mevcut alışkanlıkları: {', '.join(habits) if habits else 'henüz yok'}. Türkçe olarak 3 yeni alışkanlık öner. Her öneriyi tek satırda, emoji ile başlat. Sadece liste ver, açıklama yazma."
            }]
        )
        suggestions = message.content[0].text
        return jsonify({'suggestions': suggestions})
    except Exception as e:
        return jsonify({'suggestions': '❌ AI şu an kullanılamıyor.'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)