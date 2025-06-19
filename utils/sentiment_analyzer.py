
from transformers import pipeline
from models.models import CommentSentiment

class SentimentAnalyzer:
    _instance = None # Singleton pattern
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SentimentAnalyzer, cls).__new__(cls)
            # Initialize the model only once
            cls._model = cls._instance._load_model()
        return cls._instance

    def _load_model(self):
        model_name = "nlptown/bert-base-multilingual-uncased-sentiment"
        try:
            print(f"Loading sentiment analysis model: {model_name}")
            return pipeline("sentiment-analysis", model=model_name)
        except Exception as e:
            print(f"Error loading sentiment model: {e}")
            print("Falling back to dummy analyzer. Please check your internet connection or model name.")
            return self._dummy_analyzer

    def _dummy_analyzer(self, text):
        """A fallback dummy analyzer if the real model fails to load."""
        return [{'label': 'NEUTRAL', 'score': 1.0}]

    def analyze(self, text):
        if not self._model: 
            return CommentSentiment.NEUTRAL

        try:
            # The model outputs labels like '1 star' to '5 stars'. We map them.
            # 1 star: very negative
            # 2 stars: negative
            # 3 stars: neutral
            # 4 stars: positive
            # 5 stars: very positive
            result = self._model(text)[0]
            label = result['label']
            score = result['score']

            if 'stars' in label: # Handle nlptown model's star rating output
                star_rating = int(label.split(' ')[0])
                if star_rating <= 2:
                    return CommentSentiment.NEGATIVE
                elif star_rating == 3:
                    return CommentSentiment.NEUTRAL
                else: # 4 or 5 stars
                    return CommentSentiment.POSITIVE
            else: 
                if label.upper() == 'POSITIVE':
                    return CommentSentiment.POSITIVE
                elif label.upper() == 'NEGATIVE':
                    return CommentSentiment.NEGATIVE
                else:
                    return CommentSentiment.NEUTRAL
        except Exception as e:
            print(f"Error analyzing sentiment for text '{text}': {e}")
            return CommentSentiment.NEUTRAL 

sentiment_analyzer = SentimentAnalyzer()