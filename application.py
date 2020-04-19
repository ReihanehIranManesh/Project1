import os
import requests
import math


from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))
@app.route("/", methods=["GET"])
def index():
    if session.get("user_id") is None:
       return render_template("index.html")
    return redirect(url_for('home'))

@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")

@app.route("/login_check", methods=["POST"])
def login_check():
    username = request.form.get("username")
    password = request.form.get("psw")
    if username == "" or password == ""  :
       return render_template('login.html', message = "Please fill in the required fields.")
    elif db.execute("SELECT * FROM users WHERE username = :username AND password = :password", {"username": username, "password" : password}).rowcount == 0 :
       return render_template('login.html', message = "Your username and password do not match. Please try again.")
    session["user_id"] = db.execute("SELECT id FROM users WHERE username = :username AND password = :password", {"username": username, "password" : password}).fetchone()
    return redirect(url_for('home'))

@app.route("/join", methods=["GET"])
def join():
    return render_template("join.html")

@app.route("/join_check", methods=["POST"])
def join_check():
    username = request.form.get("username")
    password = request.form.get("psw")
    confirmpassword = request.form.get("confirmpsw")
    if username == "" or password == "" or confirmpassword == "" :
       return render_template('join.html', message = "Please fill in the required fields.")
    elif db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).rowcount != 0 :
       return render_template('join.html', message = "The username already exists. Please use a different username.")
    elif password != confirmpassword :
       return render_template('join.html', message = "Your password and confirmation password do not match.")
    db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
    {"username": username, "password" : password})
    session["user_id"] = db.execute("SELECT id FROM users WHERE username = :username AND password = :password", {"username": username, "password" : password}).fetchone()
    db.commit()
    return redirect(url_for('home'))
@app.route("/home", methods=["GET", "POST"])
def home():
    if session.get("user_id") is None:
       return render_template("index.html")
    id = session["user_id"][0]
    username = db.execute("SELECT username FROM users WHERE id = :id", {"id": id}).fetchone()
    if request.method == "GET" or request.form.get("searchinput") == "" :
       return render_template("home.html", results = "Nothing", username = username[0])
    elif request.method == "POST" :
       searchinput = request.form.get("searchinput")
       results = db.execute(f"SELECT * FROM books WHERE isbn LIKE '%{searchinput}%' OR title LIKE '%{searchinput}%' OR author LIKE '%{searchinput}%' ").fetchall()
       newsearchinput = searchinput[0].upper()
       newsearchinput += searchinput[1:]
       newresults = db.execute(f"SELECT * FROM books WHERE isbn LIKE '%{newsearchinput}%' OR title LIKE '%{newsearchinput}%' OR author LIKE '%{newsearchinput}%' ").fetchall()
       if results != newresults:
          results += newresults
       return render_template("home.html", results = results, username = username[0])
@app.route("/logout", methods=["GET"])
def logout():
    session["user_id"] = None
    return redirect(url_for('index'))

@app.route("/book/<string:title>", methods=["GET"])
def book(title):
    isbn = db.execute("SELECT isbn FROM books WHERE title = :title", {"title": title}).fetchone()
    info = db.execute("SELECT * FROM books WHERE title = :title", {"title": title}).fetchall()
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "Hr29goJUQ60kGjJh0w8WoQ", "isbns": isbn})
    if res.status_code != 200 :
       raise Exception("ERORR: API request unsuccessful.")
    data = res.json()
    work_ratings_count = data["books"][0]["work_ratings_count"]
    average_rating = data["books"][0]["average_rating"]
    temp = float(average_rating)
    avg = math.trunc(float(average_rating))
    boolean = True
    if temp - avg < 0.25:
       avgnum = avg
    elif temp - avg >= 0.25 and temp - avg < 0.75 :
       avgnum = avg
       boolean = False
    else :
       avgnum = avg + 1
    book_id = db.execute("SELECT id FROM books WHERE title = :title", {"title": title}).fetchone()
    results = db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {"book_id": book_id[0]}).fetchall()
    users = db.execute("SELECT username FROM users").fetchall()
    return render_template('book.html', work_ratings_count = work_ratings_count, average_rating = average_rating, info = info, avgnum = avgnum, boolean = boolean,  results = results, users = users)

@app.route("/review/<string:title>", methods=["GET"])
def review(title):
    author = db.execute("SELECT author FROM books WHERE title = :title", {"title": title}).fetchone()
    return render_template('review.html',  author = author, title = title )

@app.route("/submit_review/<string:title>", methods=["POST"])
def submitreview(title):
    rate = request.form.get("rate")
    reviewtxt = request.form.get("reviewtxt")
    author = db.execute("SELECT author FROM books WHERE title = :title", {"title": title}).fetchone()
    book_id = db.execute("SELECT id FROM books WHERE title = :title", {"title": title}).fetchone()
    user_id = session["user_id"]
    if rate is None:
       return render_template('review.html', message = "Please fill in the rating stars.", title = title, author = author)
    elif db.execute("SELECT * FROM reviews WHERE user_id = :user_id AND book_id = :book_id", {"user_id": user_id[0], "book_id" : book_id[0]}).rowcount != 0 :
       return render_template('review.html', message = "It appears that you have submitted a review for this book", title = title, author = author)
    db.execute("INSERT INTO reviews (user_id, book_id, review, rate) VALUES (:user_id, :book_id, :review, :rate)",
    {"user_id": user_id[0], "book_id" : book_id[0], "review": reviewtxt, "rate": rate})
    db.commit()
    return redirect(url_for('book', title = title))
@app.route("/api/<string:isbn>")
def book_api(isbn):
    book_info = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    if book_info is None:
       return jsonify({"error" : "Invalid ISBN"}), 404
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "Hr29goJUQ60kGjJh0w8WoQ", "isbns": isbn})
    if res.status_code != 200 :
       raise Exception("ERORR: API request unsuccessful.")
    data = res.json()
    work_ratings_count = data["books"][0]["work_ratings_count"]
    average_rating = data["books"][0]["average_rating"]
    return jsonify({
    "title": book_info.title,
    "author": book_info.author,
    "year": book_info.year,
    "isbn": book_info.isbn,
    "review_count": work_ratings_count,
    "average_score": average_rating
    })
