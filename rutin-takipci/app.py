from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'rutin-takipci-secret-2024')

database_url = os.environ.get('DATABASE_URL', 'sqlite:///rutin.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
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
    freeze_count = db.Column(db.Integer, default=3)
    onboarded = db.Column(db.Boolean, default=False)
    avatar = db.Column(db.String(10), default='🎯')
    avatar_color = db.Column(db.String(20), default='#6366f1')
    habits = db.relationship('Habit', backref='user', lazy=True, cascade='all, delete-orphan')
    todos = db.relationship('Todo', backref='user', lazy=True, cascade='all, delete-orphan')

class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='Genel')
    category_emoji = db.Column(db.String(10), default='📌')
    note = db.Column(db.String(300), default='')
    order = db.Column(db.Integer, default=0)
    weekly_goal = db.Column(db.Integer, default=7)
    priority = db.Column(db.String(10), default='normal')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    logs = db.relationship('HabitLog', backref='habit', lazy=True, cascade='all, delete-orphan')

class HabitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    is_freeze = db.Column(db.Boolean, default=False)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(300), nullable=False)
    done = db.Column(db.Boolean, default=False)
    date = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='accepted')

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

def get_weekly_count(habit):
    log_dates = {l.date for l in habit.logs}
    count = 0
    for i in range(7):
        d = date.today() - timedelta(days=i)
        if str(d) in log_dates:
            count += 1
    return count

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
    weekly_counts = {str(h.id): get_weekly_count(h) for h in habits}
    total = len(habits)
    completed = len([h for h in habits if h.id in today_logs])
    percent = int((completed / total) * 100) if total > 0 else 0
    xp_needed = calc_xp_for_level(current_user.level)
    xp_percent = int((current_user.xp / xp_needed) * 100) if xp_needed > 0 else 0
    todos = Todo.query.filter_by(user_id=current_user.id, date=today).all()
    show_onboarding = not current_user.onboarded and total == 0
    return render_template('index.html',
        habits=habits, today=today, today_logs=today_logs,
        streaks=streaks, weekly=weekly, weekly_counts=weekly_counts,
        total=total, completed=completed, percent=percent,
        user=current_user, xp_needed=xp_needed, xp_percent=xp_percent,
        todos=todos, show_onboarding=show_onboarding)

@app.route('/onboarding', methods=['POST'])
@login_required
def onboarding():
    habits = request.form.getlist('habits')
    for name in habits:
        if name and not Habit.query.filter_by(name=name, user_id=current_user.id).first():
            max_order = db.session.query(db.func.max(Habit.order)).filter_by(user_id=current_user.id).scalar() or 0
            habit = Habit(name=name, category=request.form.get(f'cat_{name}', 'Genel'),
                         note='', user_id=current_user.id, order=max_order+1)
            db.session.add(habit)
    current_user.onboarded = True
    db.session.commit()
    return redirect(url_for('index'))

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
    category_emoji = request.form.get('category_emoji', '📌')
    note = request.form.get('note', '')
    if name and not Habit.query.filter_by(name=name, user_id=current_user.id).first():
        max_order = db.session.query(db.func.max(Habit.order)).filter_by(user_id=current_user.id).scalar() or 0
        habit = Habit(name=name, category=category, category_emoji=category_emoji,
                     note=note, user_id=current_user.id, order=max_order+1)
        db.session.add(habit)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit/<int:habit_id>', methods=['POST'])
@login_required
def edit_habit(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    habit.name = request.form.get('name', habit.name)
    habit.category = request.form.get('category', habit.category)
    habit.category_emoji = request.form.get('category_emoji', habit.category_emoji)
    habit.note = request.form.get('note', habit.note)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/habit/goal/<int:habit_id>', methods=['POST'])
@login_required
def set_goal(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    habit.weekly_goal = int(request.form.get('goal', 7))
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

@app.route('/freeze/<int:habit_id>')
@login_required
def freeze_habit(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    yesterday = str(date.today() - timedelta(days=1))
    existing = HabitLog.query.filter_by(habit_id=habit_id, date=yesterday).first()
    if not existing and current_user.freeze_count > 0:
        log = HabitLog(habit_id=habit_id, date=yesterday, is_freeze=True)
        db.session.add(log)
        current_user.freeze_count -= 1
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

@app.route('/log/add/<int:habit_id>', methods=['POST'])
@login_required
def log_add(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    log_date = request.form.get('date')
    if log_date:
        existing = HabitLog.query.filter_by(habit_id=habit_id, date=log_date).first()
        if not existing:
            log = HabitLog(habit_id=habit_id, date=log_date)
            db.session.add(log)
            db.session.commit()
    return redirect(url_for('index'))

@app.route('/log/remove/<int:habit_id>', methods=['POST'])
@login_required
def log_remove(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    log_date = request.form.get('date')
    if log_date:
        log = HabitLog.query.filter_by(habit_id=habit_id, date=log_date).first()
        if log:
            db.session.delete(log)
            db.session.commit()
    return redirect(url_for('index'))

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

@app.route('/monthly-summary')
@login_required
def monthly_summary():
    today = date.today()
    first_day = today.replace(day=1)
    last_month_last = first_day - timedelta(days=1)
    last_month_first = last_month_last.replace(day=1)
    habits = current_user.habits
    summary = []
    for h in habits:
        log_dates = {l.date for l in h.logs}
        days_in_month = (last_month_last - last_month_first).days + 1
        completed = sum(1 for i in range(days_in_month)
                       if str(last_month_first + timedelta(days=i)) in log_dates)
        summary.append({
            'name': h.name,
            'category': h.category,
            'completed': completed,
            'total_days': days_in_month,
            'percent': int((completed / days_in_month) * 100),
            'streak': get_streak(h)
        })
    return jsonify({
        'month': last_month_last.strftime('%B %Y'),
        'username': current_user.username,
        'summary': summary,
        'total_xp': current_user.xp,
        'level': current_user.level
    })

@app.route('/leaderboard')
@login_required
def leaderboard():
    friendships = Friendship.query.filter_by(user_id=current_user.id, status='accepted').all()
    friend_ids = [f.friend_id for f in friendships] + [current_user.id]
    users = User.query.filter(User.id.in_(friend_ids)).all()
    board = []
    for u in users:
        total_xp = u.level * 100 + u.xp
        max_streak = max((get_streak(h) for h in u.habits), default=0)
        board.append({
            'username': u.username,
            'level': u.level,
            'xp': u.xp,
            'total_xp': total_xp,
            'streak': max_streak,
            'habits': len(u.habits),
            'is_me': u.id == current_user.id
        })
    board.sort(key=lambda x: x['total_xp'], reverse=True)
    for i, b in enumerate(board):
        b['rank'] = i + 1
    return jsonify(board)

@app.route('/todo/add', methods=['POST'])
@login_required
def todo_add():
    text = request.form.get('text')
    if text:
        todo = Todo(text=text, date=str(date.today()), user_id=current_user.id)
        db.session.add(todo)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/todo/done/<int:todo_id>')
@login_required
def todo_done(todo_id):
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()
    todo.done = not todo.done
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/todo/delete/<int:todo_id>')
@login_required
def todo_delete(todo_id):
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/friends')
@login_required
def friends():
    sent = Friendship.query.filter_by(user_id=current_user.id, status='accepted').all()
    friends_list = []
    for f in sent:
        friend = User.query.get(f.friend_id)
        if friend:
            max_streak = max((get_streak(h) for h in friend.habits), default=0)
            friends_list.append({'user': friend, 'streak': max_streak})
    return jsonify({
        'friends': [{'username': f['user'].username, 'level': f['user'].level,
                    'streak': f['streak'], 'habits': len(f['user'].habits)} for f in friends_list]
    })

@app.route('/friends/add', methods=['POST'])
@login_required
def friend_add():
    username = request.form.get('username')
    user = User.query.filter_by(username=username).first()
    if not user or user.id == current_user.id:
        return redirect(url_for('index'))
    existing = Friendship.query.filter_by(user_id=current_user.id, friend_id=user.id).first()
    if not existing:
        db.session.add(Friendship(user_id=current_user.id, friend_id=user.id))
        db.session.add(Friendship(user_id=user.id, friend_id=current_user.id))
        db.session.commit()
    return redirect(url_for('index'))

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
            model="claude-sonnet-4-6",
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

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)