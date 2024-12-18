import sys
import threading
import socket
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import os
import json
import subprocess
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['REPORT_FOLDER'] = os.path.join(os.getcwd(),'jacoco')

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# 定时任务存储文件
TASKS_FILE = "tasks.json"

REPORT_PORT = 8989
REPORT_DIR = app.config['REPORT_FOLDER']
http_server_thread = None


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 数据库模型
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

# 初始化数据库
with app.app_context():
    db.create_all()

# 定时任务调度器
scheduler = BackgroundScheduler()
scheduler.start()

# 初始化任务文件
if not os.path.exists(TASKS_FILE):
    with open(TASKS_FILE, 'w') as f:
        json.dump([], f)


@app.route('/')
def home():
    # 如果用户已经登录，重定向到任务列表页面
    if 'user_id' in session:
        return redirect(url_for('tasks'))
    # 否则，重定向到登录页面
    return redirect(url_for('login'))


# 注册路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('注册成功，请登录！', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('tasks'))
        else:
            flash('用户名或密码错误！', 'danger')
    return render_template('login.html')

# 登出路由
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# 任务管理页面
@app.route('/tasks')
@login_required
def tasks():
    tasks = []
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, 'r') as f:
                tasks = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            tasks = []  # 文件为空或格式错误时使用空列表
    return render_template('tasks.html', tasks=tasks)

# 添加任务
@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    task_name = request.form['task_name']
    cron_expression = request.form['cron_expression']

    # 初始化任务列表
    tasks = []
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, 'r') as f:
                tasks = json.load(f)
        except json.JSONDecodeError:
            tasks = []  # 如果文件为空或损坏，初始化为空列表

    # 添加新任务
    task_id = len(tasks) + 1
    task = {'id': task_id, 'name': task_name, 'cron': cron_expression}
    tasks.append(task)

    # 添加到调度器
    trigger = CronTrigger.from_crontab(cron_expression)
    scheduler.add_job(func=execute_task, trigger=trigger, args=[task_id], id=str(task_id))

    # 保存任务
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=4)  # 写入文件，格式化为 JSON

    flash('任务添加成功！', 'success')
    return redirect(url_for('tasks'))

# 删除任务
@app.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    with open(TASKS_FILE, 'r') as f:
        tasks = json.load(f)
    tasks = [task for task in tasks if task['id'] != task_id]

    # 从调度器中移除
    scheduler.remove_job(str(task_id))

    # 保存任务
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f)

    flash('任务删除成功！', 'success')
    return redirect(url_for('tasks'))

# 立即执行任务
@app.route('/run_task/<int:task_id>')
@login_required
def run_task(task_id):
    execute_task(task_id)
    flash('任务已执行！', 'success')
    return redirect(url_for('tasks'))

# 执行任务
def execute_task(task_id):
    # 模拟执行任务
    # subprocess.run([
    #     "java", "-jar", os.getenv("JACOCO_HOME") + "/lib/jacococli.jar", "dump",
    #     "--address", "127.0.0.1", "--port", "6300", "--destfile", "testcase.exec"
    # ])
    # subprocess.run([
    #     "java", "-jar", os.getenv("JACOCO_HOME") + "/lib/jacococli.jar", "report", "testcase.exec",
    #     "--html", "./jacoco", "--xml", "jacoco.xml", "--csv", "jacoco.csv",
    #     "--classfiles", os.getenv("TARGET_HOME") + "/target/classes/",
    #     "--sourcefiles", os.getenv("TARGET_HOME") + "/src/main/java/"
    # ])
    print("执行任务：", task_id)

@app.route('/report', methods=['GET'])
@login_required
def report():
    print("进入 report")

    # 获取Flask应用正在使用的端口
    try:
        # 启动 HTTP 服务，若已运行则不会重复启动
        print("开始启动服务")
        subprocess.Popen(
            ["python", "-m", "http.server", str(REPORT_PORT)],
            cwd=REPORT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        report_url = f"http://127.0.0.1:{REPORT_PORT}"
        print(f"Report URL: {report_url}")  # 调试日志
        return jsonify({"url": report_url})
    except Exception as e:
        print(f"Error: {e}")  # 调试日志
        return jsonify({"error": "服务启动失败"}), 500



# @app.route('/report', methods=['GET'])
# @login_required
# def report():
#     return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
