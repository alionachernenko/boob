from datetime import datetime, timedelta
from schedule import repeat, every, run_pending
import os
import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class Bot:
    def __init__(self, slack_token):
        self.client = WebClient(token=slack_token)
        self.analyzer = SentimentIntensityAnalyzer()
        convos = self.client.conversations_list()
        self.channel_id = convos["channels"][0]["id"]

    def get_sentiment_by_score(self, score: float) -> str:
        if score >= 0.05:
            return "positive"
        elif score <= -0.05:
            return "negative"
        return "neutral"

    def get_messages(self,):
        now = datetime.now()
        oldest_timestamp = int((now - timedelta(days=1)).timestamp())

        try:
            history = self.client.conversations_history(
                channel=self.channel_id,
                oldest=oldest_timestamp
            )

            return [msg for msg in history.get("messages") if "text" in msg]
        except SlackApiError as e:
            print(f"Error fetching messages: {e}")
            return []

    def analyze_messages(self, messages):
        results = []

        for message in messages:
            if ("BOOB IS HERE" in message["text"]):
                continue
            try:
                sentiment_scores = self.analyzer.polarity_scores(
                    message["text"])
                compound_score = sentiment_scores['compound']
                sentiment = self.get_sentiment_by_score(compound_score)

                result = {
                    "text": message["text"],
                    "user": message["user"],
                    "score": compound_score,
                    "sentiment": sentiment
                }

                results.append(result)
            except Exception as e:
                print(f"Error analyzing message: {e}")

        if not results:
            return None

        most_positive = max(results, key=lambda x: x["score"])
        most_negative = min(results, key=lambda x: x["score"])

        overall_score = sum(result["score"]
                            for result in results) / len(results)

        overall_sentiment = self.get_sentiment_by_score(overall_score)

        return {
            "most_positive_message": most_positive,
            "most_negative_message": most_negative,
            "overall": overall_sentiment,
        }

    def generate_report(self, result):
        if not result:
            return "No messages to analyze today! 🤷‍♀️"

        most_positive = result["most_positive_message"]
        most_negative = result["most_negative_message"]
        user_1 = most_positive["user"]
        user_2 = most_negative["user"]

        overall_sentiment = result["overall"]

        report = f"""😘 *BOOB IS HERE WITH A DAILY REPORT* 🤓

                    *Overall Mood*: *{overall_sentiment.upper()}*

                    🧚🏻 *Most Positive Message*:
                    _{most_positive['text']}_ by <@{user_1}>

                    👹 *Most Negative Message*:
                    _{most_negative['text']}_ by <@{user_2}>
                    """

        return report

    def send_report(self, report):
        try:
            self.client.chat_postMessage(
                channel=self.channel_id,
                text=report,
                parse="full"
            )
        except SlackApiError as e:
            print(f"Error sending report: {e}")


@repeat(every().day.at("18:00"))
def send_report_daily():
    SLACK_TOKEN = os.environ["TOKEN"]

    boob = Bot(SLACK_TOKEN)
    messages = boob.get_messages()
    result = boob.analyze_messages(messages)
    report = boob.generate_report(result)
    boob.send_report(report)

def main():
    while True:
        run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
