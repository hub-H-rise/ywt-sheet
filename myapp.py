from flask import Flask,render_template,request,redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import pytz
from datetime import datetime
import os
from dotenv import load_dotenv

app = Flask(__name__)

db=SQLAlchemy()
load_dotenv()
USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
HOST = os.getenv("DB_HOST")
PORT = os.getenv("DB_PORT")
NAME = os.getenv("DB_NAME")

SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}"
app.config["SQLALCHEMY_DATABASE_URI"]=SQLALCHEMY_DATABASE_URI
db.init_app(app)

migrate=Migrate(app,db)

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    posts = db.relationship('Post', backref='goal', lazy=True,cascade="all, delete")

class Post(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    done=db.Column(db.String(100),nullable=False)
    learned=db.Column(db.String(100),nullable=False)
    next_action=db.Column(db.String(100),nullable=False)
    tokyo_timezone=pytz.timezone("Asia/Tokyo")
    created_at=db.Column(db.DateTime,nullable=False,default=datetime.now(tokyo_timezone))
    goal_id = db.Column(db.Integer, db.ForeignKey('goal.id'), nullable=False)

@app.route("/")
def index():
  current_goal = Goal.query.filter_by(is_active=True).first()
  if not current_goal:
    return redirect('/goals')
  return redirect('/admin')
    
    
@app.route("/admin")
def admin():
  current_goal = Goal.query.filter_by(is_active=True).first()
  if current_goal:
    posts = Post.query.filter_by(goal_id=current_goal.id).order_by(Post.id.desc()).all()
  else:
    posts = []
  return render_template("admin.html", current_goal=current_goal, posts=posts)

@app.route("/goals", methods=["GET", "POST"])
def goals():
  if request.method == "POST":
    Goal.query.update({"is_active": False})
    if request.form.get("title"):
      new_goal = Goal(title=request.form.get("title"), is_active=True)
      db.session.add(new_goal)
    elif request.form.get("goal_id"):
      goal = Goal.query.get(request.form.get("goal_id"))
      goal.is_active = True 
    db.session.commit()
    return redirect("/admin")
    
  return render_template("goals.html", goals=Goal.query.all())
  
@app.route("/<int:goal_id>/delete_goal",methods=["POST"])
def delete_goal(goal_id):
 goal = Goal.query.get(goal_id) 
 db.session.delete(goal) 
 db.session.commit() 
 return redirect('/goals')

@app.route("/create",methods=["GET","POST"])
def create():
  if request.method == 'GET':
    return render_template('create.html')
  elif request.method == 'POST':
    done = request.form.get('done') 
    learned = request.form.get('learned')
    next_action = request.form.get('next_action')
    current_goal = Goal.query.filter_by(is_active=True).first()
    if not current_goal:
      return "アクティブな目標が設定されていません。先に目標を作成してください。"
    post = Post(done=done, learned=learned,next_action=next_action,goal=current_goal) 
    db.session.add(post) 
    db.session.commit() 
  return redirect("/admin")

@app.route("/<int:post_id>/update",methods=["GET","POST"])
def update(post_id):
  post=Post.query.get(post_id)
  if request.method == 'POST':
    post.done = request.form.get('done') 
    post.learned = request.form.get('learned')
    post.next_action = request.form.get('next_action')
    db.session.commit() 
    return redirect("/admin")
  elif request.method == 'GET':
    return render_template('update.html',post=post)
  
@app.route("/<int:post_id>/delete_post")
def delete_post(post_id):
 post = Post.query.get(post_id)
 db.session.delete(post)
 db.session.commit()
 return redirect('/admin')