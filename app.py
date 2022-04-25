from flask import Flask, render_template, request, url_for, redirect, session
import pymongo
# import bcrypt
import numpy as np
import pandas as pd
from flask import Flask, render_template, request
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
# import json
import pickle

# load the nlp model and tfidf vectorizer from disk
filename = 'nlp_model.pkl'
clf = pickle.load(open(filename, 'rb'))
vectorizer = pickle.load(open('tranform.pkl','rb'))

def create_sim():
    data = pd.read_csv('final_data.csv')
    # creating a count matrix
    cv = CountVectorizer()
    count_matrix = cv.fit_transform(data['comb'])
    # creating a similarity score matrix
    sim = cosine_similarity(count_matrix)
    return data,sim


def rcmd(m):
    m = m.lower()
    # check if data and sim are already assigned
    # try:
    #     data.head()
    #     sim.shape
    # except:
    data, sim = create_sim()
    # check if the movie is in our database or not
    if m not in data['movie_title'].unique():
        return('Sorry! This movie is not in our database. Please check the spelling or try with some other movies')
    else:
        # getting the index of the movie in the dataframe
        i = data.loc[data['movie_title']==m].index[0]

        # fetching the row containing similarity scores of the movie
        # from similarity matrix and enumerate it
        lst = list(enumerate(sim[i]))

        # sorting this list in decreasing order based on the similarity score
        lst = sorted(lst, key = lambda x:x[1] ,reverse=True)

        # taking top 1- movie scores
        # not taking the first index since it is the same movie
        lst = lst[1:11]

        # making an empty list that will containg all 10 movie recommendations
        l = []
        for i in range(len(lst)):
            a = lst[i][0]
            l.append(data['movie_title'][a])
        return l

app = Flask(__name__)

app.secret_key = "testing"
client = pymongo.MongoClient("mongodb://localhost:27017/cmrs")
db = client.get_database('cmrs')
records = db.users

@app.route('/')
def hello():
    return redirect(url_for("login"))

@app.route("/signup", methods=['post', 'get'])
def signup():
    message = ''
    if "email" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        user = request.form.get("name")
        email = request.form.get("email")
        
        password1 = request.form.get("password")
        password2 = request.form.get("confirm_password")
        
        user_found = records.find_one({"username": user})
        email_found = records.find_one({"email": email})
        if user_found:
            message = 'There already is a user by that name'
            return render_template('signup.html', message=message)
        if email_found:
            message = 'This email already exists in database'
            return render_template('signup.html', message=message)
        if password1 != password2:
            message = 'Passwords should match!'
            return render_template('signup.html', message=message)
        else:
            # hashed = bcrypt.hashpw(password2.encode('utf-8'), bcrypt.gensalt())
            user_input = {'name': user, 'email': email, 'password': password2, 'reviews': [],'recommendations': []}
            records.insert_one(user_input)
            
            user_data = records.find_one({"email": email})
            new_email = user_data['email']
            return render_template('login.html')
    return render_template('signup.html')

# @app.route('/dashboard')
# def dashboard():
#     if "email" in session:
#         data = {}
#         email = session["email"]
#         data['email'] = email
#         data['message'] = ''
#         user_data = records.find_one({"email": email})
#         movies = []
#         for i in user_data['reviews']:
#             for k in i.keys():
#                 if i[k] == 'Good':
#                     movies.append(k)
#         recommendations = []
#         for movie in movies:
#             r = rcmd(movie)
#             for i in r:
#                 recommendations.append(i)
#         recommendations = list(set(recommendations))
#         if len(user_data['reviews']) == 0:
#             data['message'] = 'You have not given any reviews!'
#             return render_template('dashboard.html', data=data)
#         else:
#             return render_template('dashboard.html', data=recommendations[::-1],len = len(recommendations))
#     else:
#         return redirect(url_for("login"))

@app.route('/dashboard')
def dashboard():
    if "email" in session:
        data = {}
        email = session["email"]
        data['email'] = email
        data['message'] = ''
        user_data = records.find_one({"email": email})
        
        if len(user_data['reviews']) == 0:
            data['message'] = 'You have not given any reviews!'
            return render_template('dashboard.html', data=data)
        else:
            return render_template('dashboard.html', data=user_data['recommendations'][::-1],len = len(user_data['recommendations']))
    else:
        return redirect(url_for("login"))

@app.route("/login", methods=["POST", "GET"])
def login():
    message = ''
    if "email" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        email_found = records.find_one({"email": email})
        if email_found:
            email_val = email_found['email']
            passwordcheck = email_found['password']
            
            # if bcrypt.checkpw(password.encode('utf-8'), passwordcheck):
            if passwordcheck == password:
                session["email"] = email_val
                return redirect(url_for('dashboard'))
            else:
                if "email" in session:
                    return redirect(url_for("dashboard"))
                message = 'Wrong password'
                return render_template('login.html', message=message)
        else:
            message = 'Email not found'
            return render_template('login.html', message=message)
    return render_template('login.html', message=message)

@app.route("/logout", methods=["POST", "GET"])
def logout():
    if "email" in session:
        session.pop("email", None)
    return redirect(url_for('login'))

@app.route("/review")
def review():
    movie = request.args.get('movie')
    d = pd.read_csv('final_data.csv')
    for i in d['movie_title']:
        if i.lower() == movie.lower():
            return render_template('review.html',movie = movie)
    return render_template('review.html',movie = '')

# @app.route('/user_review/<movie>',methods=["POST","GET"])
# def user_review(movie):
#     review = request.form.get('review')
#     email = session['email']
#     movie_review_list = np.array([review])
#     movie_vector = vectorizer.transform(movie_review_list)
#     pred = clf.predict(movie_vector)
#     r = 'Good' if pred else 'Bad'
#     user_data = records.find_one({"email": email})
#     l = user_data['reviews']
#     flag = 0
#     for j in l:
#         if movie in j.keys():
#             flag = 1
#             j[movie] = r
#             break
#     if flag == 0:
#         l.append({movie:r})
#     records.update_one({'_id':user_data['_id']},{'$set':{'reviews':l}})
#     return redirect(url_for('dashboard'))

@app.route('/user_review/<movie>',methods=["POST","GET"])
def user_review(movie):
    review = request.form.get('review')
    email = session['email']
    movie_review_list = np.array([review])
    movie_vector = vectorizer.transform(movie_review_list)
    pred = clf.predict(movie_vector)
    r = 'Good' if pred else 'Bad'
    user_data = records.find_one({"email": email})
    l = user_data['reviews']
    flag = 0
    for j in l:
        if movie in j.keys():
            flag = 1
            j[movie] = r
            break
    if flag == 0:
        l.append({movie:r})
    records.update_one({'_id':user_data['_id']},{'$set':{'reviews':l}})
    movies = []
    for i in user_data['reviews']:
        for k in i.keys():
            if i[k] == 'Good':
                movies.append(k)
    recommendations = []
    for movie in movies:
        r = rcmd(movie)
        for i in r:
            recommendations.append(i)
    recommendations = list(set(recommendations))
    records.update_one({'_id':user_data['_id']},{'$set':{'recommendations':recommendations}})
    return redirect(url_for('dashboard'))

if __name__ == "__main__":
  app.run(debug=True)
