from flask import Flask, render_template, redirect, jsonify, request
from flask_pymongo import PyMongo
from scrape_nyt import scrape
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from wordcloud import WordCloud, STOPWORDS
import pandas as pd
import numpy as np
import json
import nltk
import re
import csv
import matplotlib.pyplot as plt 
import seaborn as sns
from tqdm import tqdm
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
import pickle
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.metrics import f1_score
from sklearn.preprocessing import MultiLabelBinarizer
from nltk.corpus import stopwords
import nltk
nltk.download('stopwords')

# Create an instance of Flask
app = Flask(__name__)

# Use PyMongo to establish Mongo connection
mongo = PyMongo(app, uri="mongodb://localhost:27017/movie_app")

# Sentiment Intensity Analyzer
def sentiment_scores(review): 

    # Create a SentimentIntensityAnalyzer object. 
    sid_obj = SentimentIntensityAnalyzer() 

    # polarity_scores method of SentimentIntensityAnalyzer 
    # oject gives a sentiment dictionary. 
    # which contains pos, neg, neu, and compound scores. 
    sentiment_dict = sid_obj.polarity_scores(review) 
        

    sentiment = ""
    
    # decide sentiment as positive, negative and neutral 
    if sentiment_dict['compound'] >= 0.05 : 
        #print("Positive") 
        sentiment = "Positive"
    elif sentiment_dict['compound'] <= - 0.05 : 
        #print("Negative") 
        sentiment = "Negative"
    else : 
        #print("Neutral") 
        sentiment = "Neutral"

    return sentiment 

# Route to render index.html template using data from Mongo
@app.route("/")
def home():

    # Find one record of data from the mongo database
    # destination_data = mongo.db.movie_data.find_one()

    # Return template and data
    # return render_template("index.html", movie_data=destination_data)
    return render_template("index1.html")

# Route that will trigger the scrape function
@app.route("/scrape", methods =["GET","POST"])
def scrapepage():
    
    if request.method == "POST":
     
    # Run the scrape function
        #movie_data = scrape()

    # Update the Mongo database using update and upsert=True
        
        movietitle = request.form["movietitle"]
        #print(movietitle)
        movieyear = request.form["movieyear"]
        #print(movieyear)

    movie_data = scrape(movietitle, movieyear)
    mongo.db.movie_data.update({}, movie_data, upsert=True)
    # Redirect back to home page

    movie_data = mongo.db.movie_data.find_one()

    # Create DataFrame for Review Text
    df = pd.DataFrame(columns =["reviewText"])
    df.loc[0] = movie_data["review_text"]
     
   
    # # Split Review Text
    comment_words = ' '
    stopwords = set(STOPWORDS)

    x=[]
    for word in df.reviewText:
        word = str(word)
        tokens = word.split()
        
        for words in tokens:
            
            if words not in stopwords:
                x.append(words)
    comment_words = ''.join(x)
    
        
    movie_data["review_sentiment"] = sentiment_scores(comment_words)
    try: 
        movie_data["pred_genre"] = infer_tags_prob(movie_data["plot"])[0][0]
    except:
        movie_data["pred_genre"] = "Unpredictable"

     # Create wordcloud

    wordcloud = WordCloud(width = 800, height = 800,
        max_words = 100,
        background_color ='white',
        stopwords = stopwords,
        min_font_size = 10).generate(movie_data["review_text"])

   # plot the WordCloud image
    plt.figure(figsize = (8, 8), facecolor = None)
    plt.imshow(wordcloud)
    plt.axis("off")
    plt.tight_layout(pad = 0)

    plt.savefig('static/wordcloud.png')

    
    
    return render_template("index.html", movie_data=movie_data)
   
# function for text cleaning 
def clean_text(text):
    # remove backslash-apostrophe 
    text = re.sub("\'", "", text) 
    # remove everything except alphabets 
    text = re.sub("[^a-zA-Z]"," ",text) 
    # remove whitespaces 
    text = ' '.join(text.split()) 
    # convert text to lowercase 
    text = text.lower() 
    
    return text

# nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

# function to remove stopwords
def remove_stopwords(text):
    no_stopword_text = [w for w in text.split() if not w in stop_words]
    return ' '.join(no_stopword_text)


# load the model from disk
modelname = 'movie_genrepredict.sav'
clf = pickle.load(open(modelname, 'rb'))

transformname = 'movie_genretranformpredict.sav'
tfidf_vectorizer = pickle.load(open(transformname, 'rb'))

multiname = 'movie_genreyvaluepredict.sav'
multilabel_binarizer = pickle.load(open(multiname, 'rb'))

def infer_tags_prob(q, t=0.3):
    q = clean_text(q) ## Defined function for clean
    q = remove_stopwords(q) ## Defined function for removing stop words
    q_vec = tfidf_vectorizer.transform([q]) ##create TF-IDF features 
    q_pred = clf.predict_proba(q_vec) ## The models predict.
    q_pred_new = (q_pred >= t).astype(int)
    return multilabel_binarizer.inverse_transform(q_pred_new)

movie_data = mongo.db.movie_data.find_one()
#print(movie_data)
#movie_plot = "This food was absolutely the worst thing I have ever eaten, stomach thought I was eating Taco Bell and tongue thought I was eating dirt."
# print("Predicted genre: ", infer_tags_prob(movie_plot))
print("Predicted genre: ", ', '.join(infer_tags_prob(movie_data["plot"])[0]))



if __name__ == "__main__":
    app.run(debug=True)
