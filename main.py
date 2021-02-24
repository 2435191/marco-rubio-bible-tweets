import twint
import re
import os
import pandas
import datetime
import matplotlib.pyplot as plt
import matplotlib as mpl
import json

# from wikipedia, map abbreviations to full bible verse names
with open('verses.json') as verses_json:
    verses_map = json.load(verses_json)

def is_bible_verse(s: str) -> bool:
    """
    Does a text contain reference to a part of the Bible?
    example: is_bible_verse("text filler blah blah 1 Mark  23: 45-67   ") -> True
    """
    re_pattern = r"((?:\d +)?[A-Za-z]+) +(\d\d?) +(\d\d?-\d\d?|\d\d?)(?: +|$)"
    s = s.replace(';', ' ').replace(':', ' ')

    res = re.findall(re_pattern, s, flags=re.IGNORECASE)
    return bool(res)


def get_tweets() -> pandas.DataFrame:
    """
    Get all of @marcorubio's tweets that have a Bible verse (or abbreviation) and put them in a DataFrame.
    """
    df = pandas.DataFrame(columns=["id", "verse", "tweet", 'datetime', 'date', "link", "replies_count", "retweets_count", "likes_count"]).set_index('id')
    
    for verse in verses_map.keys():
        print(verse)
        twint.output.clean_lists()

        c = twint.Config()
        c.Username = "marcorubio"
        c.Search = verse
        c.Filter_retweets = True
        c.Store_object = True
        twint.run.Search(c)
        tweets = twint.output.tweets_list
        
        for tweet in tweets:
            df.loc[tweet.id, :] = [
                verse,
                tweet.tweet,
                tweet.datetime,
                tweet.datestamp,
                tweet.link,
                tweet.replies_count,
                tweet.retweets_count,
                tweet.likes_count
            ]
    df['verse_full'] = df['verse'].map(verses_map)
    df['is_verse'] = df['tweet'].apply(is_bible_verse)
    return df

def get_number_tweets_for_month(ts: datetime.datetime) -> int:
    """
    Get the total number of tweets that @marcorubio made in `ts.month`. 
    TODO: Possibly approximate, maybe splitting into two tasks (two weeks each) would fix.
    """
    c = twint.Config()
    c.Username = "marcorubio"
    c.Filter_retweets = True
    c.Since = ts.replace(day=1).strftime('%Y-%m-%d')
    # yeah this part's a bit janky, especially the day=2 bit. Don't know of a fix, and returns too few results otherwise
    c.Until = ts.replace(day=2, month=ts.month%12+1, year=ts.year+1 if ts.month==12 else None).strftime('%Y-%m-%d') 

    c.Store_object = True
    twint.run.Search(c)
    
    lst = twint.output.tweets_list
    twint.output.clean_lists()

    return len(lst)

def group(df: pandas.DataFrame) -> pandas.DataFrame:
    """
    Do some cleaning operations and get the total number of tweets for each month.
    """
    df['date'] = pandas.to_datetime(df['date'])
    df.reset_index(inplace=True)
    
    df = df['tweet'].groupby(df['date'].dt.to_period('M')).count().resample('M').asfreq().fillna(0).to_frame()
    df.index = df.index.to_timestamp()
    df.rename({'tweet': 'bible_tweet_count'}, axis=1, inplace=True)

    df['total_tweets'] = df.index.map(get_number_tweets_for_month)

    return df



if __name__ == "__main__":
    
    if os.path.exists('data.csv'):
        df = pandas.read_csv('data.csv')
    else:
        df = get_tweets()
        df.to_csv('data.csv')

    grouped = group(df)
    grouped.to_csv('grouped.csv')
    