import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from typing import Callable, Any
from wsgiref.simple_server import make_server
from urllib.parse import parse_qs

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

AVAILABLE_LOCATIONS = [
    "Albuquerque, New Mexico",
    "Carlsbad, California",
    "Chula Vista, California",
    "Colorado Springs, Colorado",
    "Denver, Colorado",
    "El Cajon, California",
    "El Paso, Texas",
    "Escondido, California",
    "Fresno, California",
    "La Mesa, California",
    "Las Vegas, Nevada",
    "Los Angeles, California",
    "Oceanside, California",
    "Phoenix, Arizona",
    "Sacramento, California",
    "Salt Lake City, Utah",
    "Salt Lake City, Utah",
    "San Diego, California",
    "Tucson, Arizona",
]

class ReviewAnalyzerServer:
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        pass

    def analyze_sentiment(self, review_body):
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """

        if environ["REQUEST_METHOD"] == "GET":
            query_string = parse_qs(environ["QUERY_STRING"])
            new_reviews = reviews.copy()
            
            LOCATION_FILTER = lambda review: review['Location'] == query_string["location"][0]

            def START_DATE_FILTER(review): 
                timestamp = datetime.strptime(review['Timestamp'], "%Y-%m-%d %H:%M:%S") 
                start_date = datetime.strptime(query_string["start_date"][0], "%Y-%m-%d")
                return start_date <= timestamp 

            def END_DATE_FILTER(review): 
                timestamp = datetime.strptime(review['Timestamp'], "%Y-%m-%d %H:%M:%S") 
                end_date = datetime.strptime(query_string["end_date"][0], "%Y-%m-%d")
                return timestamp <= end_date

            if "location" in query_string: new_reviews = list(filter(LOCATION_FILTER, new_reviews))
            if "start_date" in query_string: new_reviews = list(filter(START_DATE_FILTER, new_reviews))
            if "end_date" in query_string: new_reviews = list(filter(END_DATE_FILTER, new_reviews))

            for review in new_reviews:
                sentiment_analysis = self.analyze_sentiment(review["ReviewBody"]);
                review["sentiment"] = sentiment_analysis
            
            response_body = json.dumps(new_reviews, indent=2).encode("utf-8")

            # Set the appropriate response headers
            start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_body)))
             ])
            
            return [response_body]


        if environ["REQUEST_METHOD"] == "POST":
            # get the payload of post request
            content_length = int(environ.get("CONTENT_LENGTH", 0))
            post_data = environ["wsgi.input"].read(content_length).decode("utf-8")
            post_data = parse_qs(post_data)

            # add the new review to the reviews list
            new_review = {
                "ReviewId": str(uuid.uuid4()),
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if "Location" in post_data and post_data["Location"][0] in AVAILABLE_LOCATIONS and "ReviewBody" in post_data:
                new_review["Location"] = post_data["Location"][0]
                new_review["ReviewBody"] = post_data["ReviewBody"][0]

                reviews.append(new_review)

                response_body = json.dumps(new_review, indent=2).encode("utf-8")

                start_response("201 OK", [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(response_body)))
                ])
            else:
                response_body = json.dumps({"error": "Missing required fields"}, indent=2).encode("utf-8")
                start_response("400 Bad Request", [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(response_body)))
                ])
                
            return [response_body]

if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()