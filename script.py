from flask import Flask
import pandas as pd
import os
import googleapiclient.discovery
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import tweepy
import requests
from flask_cors import CORS
from flask import request
from pytube import extract
import re
from collections import Counter
from nltk.corpus import stopwords


stop_words = stopwords.words('english')
stopwords_dict = Counter(stop_words)

bearer_token='AAAAAAAAAAAAAAAAAAAAABzLbAEAAAAAyJ3i49oHxSJn3ATM20aj5hw5BNc%3D1pTVqla9W10lz7IxhcA5uchHn9OUtURTj8oAKQMuDS0mE1h77A'
params = {"tweet.fields": "created_at"}


analyzer = SentimentIntensityAnalyzer()

app = Flask(__name__)
CORS(app)

# To get twitter id
def get_user_id(uname):
    response = requests.request("GET", "https://api.twitter.com/2/users/by/username/{}".format(uname), auth=bearer_oauth, params=params)
    print(response.status_code)
    if response.status_code != 200:
        raise Exception(
            "Request returned an error: {} {}".format(
                response.status_code, response.text
            )
        )
    return response.json()

# To verify bearer token for twitter
def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """

    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2UserTweetsPython"
    return r



# Sentiment score checker fucntion 1
def checker_1(c):
    if c >=0.5:
        return 'pos'
    elif c >= 0 and c < 0.5:
        return 'neu'
    else:
        return 'neg'
# Sentiment score chekcer function 2
def checker_2(c):
    if c >=0.5:
        return 'pos'
    elif c >= 0 and c < 0.5:
        return 'neu'
    else:
        return 'neg'




@app.route("/youtube", methods = ['POST'])
def youtube():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    api_service_name = "youtube"
    api_version = "v3"
    DEVELOPER_KEY = "AIzaSyDk79F6tlPXWJtvpPEJ_zs66EB8Hfyp_nE"
    # video_id = "eMGlRInFK1k"
    youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey = DEVELOPER_KEY)
    comments = []
    authors = [] 
    com_scores = [] 
    ydata = dict(request.get_json())
    ylink = ydata.get("link_data")
    print(ydata.get("link_data"))
    video_id = extract.video_id(ylink)
    print(video_id)
    
    def load_comments(match):
        for item in match["items"]:
            comment = item["snippet"]["topLevelComment"]
            author = comment["snippet"]["authorDisplayName"]
            text = comment["snippet"]["textDisplay"]
            comments.append(text)
            authors.append(author)
            
            print("Comment by {}: {}".format(author, text))
            if 'replies' in item.keys():
                for reply in item['replies']['comments']:
                    rauthor = reply['snippet']['authorDisplayName']
                    rtext = reply["snippet"]["textDisplay"]
                print("\n\tReply by {}: {}".format(rauthor, rtext), "\n")


    def get_comment_threads1(youtube, video_id, nextPageToken):
        results = youtube.commentThreads().list(
            part="snippet",
            maxResults=100,
            videoId=video_id,
            textFormat="plainText",
            pageToken = nextPageToken
        ).execute()
        return results

    def get_comment_threads2(youtube, video_id):
        results = youtube.commentThreads().list(
            part="snippet",
            maxResults=100,
            videoId=video_id,
            textFormat="plainText"
            ).execute()
        return results
    try:
        match = get_comment_threads1(youtube, video_id, '')
        next_page_token = match["nextPageToken"]
        load_comments(match)
    except:
         match = get_comment_threads2(youtube, video_id)
         load_comments(match)
    
    try:
        while next_page_token:
          match = get_comment_threads1(youtube, video_id, next_page_token)
          next_page_token = match["nextPageToken"]
          load_comments(match)
    except:
        data = pd.DataFrame(comments, index = authors,columns=["Comments"])
        sentences = data["Comments"]
        for sentence in sentences:
            temp_sent = sentence.strip()
        #     temp_sent = re.sub('[^A-Za-z0-9]+', '', temp_sent)
        #     temp_sent = re.sub('[!,*)@#%(&$_?.^]', '', temp_sent)
            temp_sent = re.sub(r"\W+", " ", temp_sent)
            temp_sent = temp_sent.lower()
            temp_sent = ' '.join([word for word in temp_sent.split() if word not in stopwords_dict])
            vs = analyzer.polarity_scores(temp_sent)
            com_scores.append(vs)
            # comp = comp + vs.get("compound")
            # print(sentence)
            print(temp_sent)

    # data['scores'] = data['Comments'].apply(lambda review: analyzer.polarity_scores(review))
    data['scores'] = com_scores
    data['compound']  = data['scores'].apply(lambda score_dict: score_dict['compound'])
    data['comp_score'] = data['compound'].apply(checker_1)
    # print(data)

    return "Sucessful!"





@app.route("/twitter", methods=['POST'])
def twitter():
#   uname = "SydneyTheFlash9"
# uname = "elonmusk"
  client = tweepy.Client(bearer_token=bearer_token)
  uname = dict(request.get_json()).get("link_data")
  print(uname)
  
  # Replace user ID
  data = get_user_id(uname).get('data')
  id = data.get('id')
#   params = {"tweet.fields": "created_at"}
  tweets = client.get_users_tweets(id=id, tweet_fields=['context_annotations','created_at','geo'])
  tweets_1 = []
  tweets_scores = []
  for tweet in tweets.data:
    temp_sent = str(tweet).strip()
    temp_sent = re.sub(r"@[A-Za-z0-9]+", '', temp_sent)
#     temp_sent = re.sub('[!,*)@#%(&$_?.^]', '', temp_sent)
    temp_sent = re.sub(r"\W+", " ", temp_sent)
    temp_sent = temp_sent.lower()
    temp_sent = ' '.join([word for word in temp_sent.split() if word not in stopwords_dict])
    vs = analyzer.polarity_scores(temp_sent)
    tweets_1.append(str(tweet))
    tweets_scores.append(vs)
#     comp = comp + vs.get("compound")
    print("{:-<65} {}".format(temp_sent, str(vs)))
#   print(tweet)

  tweets_data = pd.DataFrame(tweets_1, columns=["Tweet"])
  tweets_data["scores"] = tweets_scores
  tweets_data['compound']  =  tweets_data['scores'].apply(lambda score_dict: score_dict['compound'])
  tweets_data['comp_score'] = tweets_data['compound'].apply(checker_2)
  tweets_data
  tweets = []
  return "Successful!"


if __name__ == "__main__":
  app.run(debug=True)