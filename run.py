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
import subprocess
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['REPORT_FOLDER'] = os.path.join(os.getcwd(), 'jacoco')

REPORT_PORT = 8989
REPORT_DIR = app.config['REPORT_FOLDER']

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# 定时任务调度器
scheduler = BackgroundScheduler()
scheduler.start()

# 数据库模型
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cron = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# 初始化数据库
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
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
    # user_tasks = Task.query.filter_by(user_id=current_user.id).all()
    # return render_template('tasks.html', tasks=user_tasks, taskId=None)
    all_tasks = Task.query.all()  # 获取所有任务，而不是仅当前用户的任务
    return render_template('tasks.html', tasks=all_tasks, taskId=None)


# 添加任务
@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    current_user_obj = current_user
    if current_user_obj.username != 'admin':
        flash('只有管理员用户才能添加任务！', 'danger')
        return redirect(url_for('tasks'))

    task_name = request.form['task_name']
    cron_expression = request.form['cron_expression']
    new_task = Task(
        name=task_name,
        cron=cron_expression,
        user_id=current_user.id
    )
    db.session.add(new_task)
    db.session.commit()

    # 添加到调度器
    trigger = CronTrigger.from_crontab(cron_expression)
    scheduler.add_job(func=execute_task, trigger=trigger, args=[new_task.id], id=str(new_task.id))

    flash('任务添加成功！', 'success')
    return redirect(url_for('tasks'))

# 删除任务
@app.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get(task_id)
    if task and task.user_id == current_user.id:
        # 从调度器中移除
        scheduler.remove_job(str(task_id))
        db.session.delete(task)
        db.session.commit()
        flash('任务删除成功！', 'success')
        return redirect(url_for('tasks'))
    else:
        flash('只有管理员用户才能删除任务！', 'danger')
        return redirect(url_for('tasks'))

# 编辑任务
@app.route('/edit_task/<int:task_id>', methods=['POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get(task_id)
    if task and task.user_id == current_user.id:
        new_name = request.form['task_name']
        new_cron = request.form['cron_expression']
        task.name = new_name
        task.cron = new_cron
        db.session.commit()

        # 先从调度器中移除旧任务配置
        scheduler.remove_job(str(task_id))
        # 根据新的Cron表达式重新添加任务到调度器
        trigger = CronTrigger.from_crontab(new_cron)
        scheduler.add_job(func=execute_task, trigger=trigger, args=[task_id], id=str(task_id))

        flash('任务编辑成功！', 'success')
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

# 每天启动时重新加载任务到调度器（可以在应用启动时调用这个函数）
def load_tasks_to_scheduler():
    tasks = Task.query.all()
    for task in tasks:
        try:
            trigger = CronTrigger.from_crontab(task.cron)
            scheduler.add_job(func=execute_task, trigger=trigger, args=[task.id], id=str(task.id))
        except:
            print(f"任务 {task.id} 的Cron表达式配置可能有误，无法添加到调度器")

# 在应用启动时调用任务加载函数，确保任务能正常调度
with app.app_context():
    load_tasks_to_scheduler()

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)