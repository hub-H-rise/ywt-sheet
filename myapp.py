from flask import Flask,render_template,request,redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import pytz
from datetime import datetime,timedelta
import os
from google import genai
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
tokyo_timezone = pytz.timezone("Asia/Tokyo")


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
    created_at=db.Column(db.DateTime,nullable=False,default=lambda:datetime.now(pytz.utc).astimezone(tokyo_timezone),
  )
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
  current_goal = Goal.query.filter_by(is_active=True).first()
  if not current_goal:
    return "アクティブな目標が設定されていません。先に目標を作成してください。"
  elif request.method == 'GET':
    return render_template('create.html',current_goal=current_goal)
  elif request.method == 'POST':
    done = request.form.get('done') 
    learned = request.form.get('learned')
    next_action = request.form.get('next_action')
    current_goal = Goal.query.filter_by(is_active=True).first()
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

@app.route("/weekly_report")
def weekly_report():
  current_goal = Goal.query.filter_by(is_active=True).first()
  one_week_ago = datetime.now(tokyo_timezone) - timedelta(days=7)
  recent_posts = Post.query.filter(Post.created_at >= one_week_ago).all()
  goal_title = current_goal.title if current_goal else "設定された目標はありません"
  post_count = len(recent_posts)
  if post_count == 0:
    volume_instruction = "今週は記録がありません。短く優しく、記録をつけるメリットを伝えるメッセージにしてください。"
  elif post_count <= 2:
    volume_instruction = f"今週の記録は少なめ（{post_count}件）です。サラッと読めるコンパクトなボリュームにし、無理なく続けられるような温かいフィードバックにしてください。"
  elif post_count <= 7:
    volume_instruction = f"今週は適度なペース（{post_count}件）で記録できています。標準的なボリュームで、成果の承認とバランスの良いアドバイスを記載してください。"
  else:
    volume_instruction = f"今週は非常に多くの記録（{post_count}件）があり、アクティブに学習が進んでいます。読み応えのある充実したボリュームにし、多角的な視点からの振り返りと次のステップへの深いアドバイスを丁寧にまとめてください。"
  
  posts_text = ""
  for post in recent_posts:
    posts_text += f"- 日時: {post.created_at.strftime('%Y-%m-%d')}\n  やったこと: {post.done}\n  わかったこと: {post.learned}\n  次やること: {post.next_action}\n\n"
    
  prompt = f"""
以下のユーザーの「大きな目標」と「直近1週間のYWT活動記録」をもとに、今週の学習の成果を振り返る「週間学習レポート」を作成してください。
ポジティブなフィードバックと、来週に向けたアドバイスをわかりやすくまとめてください。

【出力ルール】
1. Markdown形式（#や**など）や、コードブロック（「```html」や「```」）は一切使用しないでください。
2. 出力はすべて、ウェブサイトにそのまま組み込める純粋なHTMLタグ（<h3>, <p>, <strong>, <ul>, <li> など）のみで行ってください。

【大きな目標】
{goal_title}

【ボリュームに関する指示】
{volume_instruction}

【直近1週間のYWT活動記録】
{posts_text if posts_text else "記録がありません"}
"""
  ai_report = "今週はまだYWTの記録がないため、レポートを生成できませんでした。日々の記録をつけてみましょう！"
    
  if recent_posts:
      try:
        client = genai.Client() 
        response = client.models.generate_content(model='gemini-3.5-flash-lite',contents=prompt)
        ai_report = response.text
      except Exception as e:
        ai_report = f"AIレポートの生成中にエラーが発生しました: {e}"

  return render_template(
        "weekly_report.html",
        current_goal=current_goal,
        recent_posts=recent_posts,
        ai_report=ai_report
    )