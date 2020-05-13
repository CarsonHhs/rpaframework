from dataclasses import dataclass
import datetime
import logging
import tweepy
from tweepy.error import TweepError
from RPA.core.utils import required_env, required_param


@dataclass
class Tweet:
    """Represents Tweet"""

    created_at: datetime.datetime
    id: int
    tweet_id_str: str
    text: str
    in_reply_to_screen_name: str
    lang: str
    name: str
    screen_name: str
    hashtags: list
    is_truncated: bool = False
    favorite_count: int = 0
    retweet_count: int = 0


class Twitter:
    """Library for managing Twitter.

    Library usage requires Twitter developer credentials, which can
    be received from https://developer.twitter.com/.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._auth = None
        self.api = None
        self._me = None

    def authorize(
        self,
        consumer_key: str = None,
        consumer_secret: str = None,
        access_token: str = None,
        access_token_secret: str = None,
    ) -> None:
        """Authorize to Twitter API

        :param consumer_key: app consumer key
        :param consumer_secret: app consumer secret
        :param access_token: user access token
        :param access_token_secret: user access token secret
        """
        consumer_key = required_env("TWITTER_CONSUMER_KEY", consumer_key)
        consumer_secret = required_env("TWITTER_CONSUMER_SECRET", consumer_secret)
        access_token = required_env("TWITTER_ACCESS_TOKEN", access_token)
        access_token_secret = required_env(
            "TWITTER_ACCESS_TOKEN_SECRET", access_token_secret
        )
        self._auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        self._auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(self._auth, wait_on_rate_limit=True)
        try:
            self.api.verify_credentials()
            self.logger.info("Twitter authentication success")
            self._me = self.api.me()
        except TweepError as e:
            self.logger.error("Error during Twitter authentication: %s", str(e))

    def get_me(self) -> dict:
        """Get Twitter profile of authenticated user

        :return: user profile as dictionary or `None`
        """
        return self._me._json if self._me else None  # pylint: disable=W0212

    def get_user_tweets(self, username: str = None, count: int = 100) -> list:
        """Get user tweets

        :param username: whose tweets to get
        :param count: maximum number of tweets, defaults to 100
        :return: list of user tweets
        """
        required_param(username, "get_user_tweets")
        tweets = []
        try:
            # Pulling individual tweets from query
            for tweet in self.api.user_timeline(id=username, count=count):
                # Adding to list that contains all tweets
                tw = Tweet(
                    created_at=tweet.created_at,
                    id=tweet.id,
                    tweet_id_str=tweet.id_str,
                    text=tweet.text,
                    in_reply_to_screen_name=tweet.in_reply_to_screen_name,
                    lang=tweet.lang,
                    name=tweet.user.name,
                    screen_name=tweet.user.screen_name,
                    hashtags=[ht["text"] for ht in tweet.entities["hashtags"]],
                    is_truncated=tweet.truncated,
                    favorite_count=tweet.favorite_count,
                    retweet_count=tweet.retweet_count,
                )
                tweets.append(tw)
        except TweepError as e:
            self.logger.warning("Twitter timeline failed: %s", str(e))
        return tweets

    def text_search_tweets(
        self,
        query: str = None,
        count: int = 100,
        geocode: str = None,
        lang: str = None,
        locale: str = None,
        result_type: str = "mixed",
        until: str = None,
        since_id: str = None,
        max_id: str = None,
    ) -> list:
        """Search tweets defined by search query

        Results types:
            - mixed : include both popular and real time results in the response
            - recent : return only the most recent results in the response
            - popular : return only the most popular results in the response

        :param query: search query string of 500 characters maximum,
            including operators
        :param count: maximum number of tweets, defaults to 100
        :param geocode: tweets by users located within a given
            radius of the given latitude/longitude
        :param lang: language code of tweets
        :param locale: language of the query you are sending
        :param result_type: type of search results you would prefer to receive,
            default "mixed"
        :param until: tweets created before the given date
        :param since_id: Returns only statuses with an ID greater than
        :param max_id: only statuses with an ID less than
        :return: list of matching tweets
        """
        required_param(query, "text_search_tweets")
        tweets = []
        try:
            # Pulling individual tweets from query
            for tweet in self.api.search(
                q=query,
                count=count,
                geocode=geocode,
                lang=lang,
                locale=locale,
                result_type=result_type,
                until=until,
                since_id=since_id,
                max_id=max_id,
            ):
                # Adding to list that contains all tweets
                tweets.append((tweet.created_at, tweet.id, tweet.text))
        except TweepError as e:
            self.logger.warning("Twitter search failed: %s", str(e))
        return tweets

    def get_user_profile(self, username: str = None):
        """Get user's Twitter profile

        :param username: whose profile to get
        :return: profile as dictionary
        """
        required_param(username, "get_user_profile")
        try:
            profile = self.api.get_user(username)
            return profile._json  # pylint: disable=W0212
        except TweepError:
            return None

    def tweet(self, content: str = None):
        """Make a tweet with content

        :param content: [description]
        """
        required_param(content, "tweet")
        self.api.update_status(content)

    def like(self, tweet):
        """Like a tweet

        :param tweet: as a class `Tweet`
        :return: `True` if Tweet was liked, `False` if not
        """
        required_param(tweet, "like")
        try:
            self.api.create_favorite(tweet.id)
            return True
        except TweepError:
            self.logger.warning(
                'Could not like tweet "%s" by user "%s"', tweet.text, tweet.screen_name,
            )
            return False

    def unlike(self, tweet):
        """Unlike a tweet

        :param tweet: as a class `Tweet`
        :return: `True` if Tweet was unliked, `False` if not
        """
        try:
            self.api.destroy_favorite(tweet.id)
            return True
        except TweepError:
            self.logger.warning(
                'Could not unlike tweet "%s" by user "%s"',
                tweet.text,
                tweet.screen_name,
            )
            return False