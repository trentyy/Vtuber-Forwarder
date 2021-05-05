import json, asyncio, sys, socket, time
import requests, urllib3
from datetime import datetime, timedelta
from dateutil.parser import isoparse
import pymysql

# my module
from APIs import youtubeAPI

DEBUG = True

with open('db_setting.json', 'r') as f:
    db_setting = json.load(f)
    f.close()
HOST=db_setting['host']
USER=db_setting['user']
PW=db_setting['password']
DB=db_setting['database']
# load data and set variables
with open('twitter_forward_setting.json','r', encoding='utf8') as f:
    t_setting = json.load(f)
    f.close()
t_url = t_setting['twitter_url']
twitter_icon_url = t_setting['twitter_icon_url']

# gen1 with staff
proproduction = t_setting['proproduction']
mikuru = t_setting['mikuru']
mia = t_setting['mia']
chiroru = t_setting['chiroru']
isumi = t_setting['isumi']
yuru = t_setting['yuru']
# gen2
mai = t_setting['mai']
rin = t_setting['rin']
aoi = t_setting['aoi']
momoa = t_setting['momoa']
azusa = t_setting['azusa']
BOX_MEMBER = (
    proproduction, 
    mikuru, mia, chiroru, isumi, yuru, 
    mai, rin, aoi, momoa, azusa)
TARGETS_GEN1 = mikuru, mia, chiroru, isumi, yuru
TARGETS_GEN2 = mai, rin, aoi, momoa, azusa      # here is TARGETS list
BOX_MEMBER_ID = [x['id'] for x in BOX_MEMBER]

with open('twitter_api.json', mode='r', encoding='utf8') as jfile:
    jdata = json.load(jfile)

class twitterTracker():
    def __init__(self):
        self.TARGETS = BOX_MEMBER
        with open('db_setting.json', 'r') as f:
            db_setting = json.load(f)
            f.close()
        self.connectDB()
    def connectDB(self, host=HOST, user=USER,
                    password=PW, database=DB):
        self.db = pymysql.connect(
            host=host, user=user, password=password, db=database,
            cursorclass=pymysql.cursors.DictCursor)
        self.cur = self.db.cursor()
    def closeDB(self):
        self.db.close()
    def loadDataList(self, 
                        select="id", 
                        where=" `isForwarded` = 0 ", 
                        extra=" ORDER BY `created_at` DESC LIMIT 1 "):
        #SELECT * FROM `tweets` WHERE `username` = 'kadukimikuru'
        sql = f"SELECT {select} FROM `tweets` WHERE {where} {extra};"
        
        try:
            result_num = self.cur.execute(sql)
            result = self.cur.fetchall()
        except Exception as e:
            time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(time+" [Error]  twitterTracker.loadDataList while execute sql:")
            print(sql)
            raise e
        return result
    def get_tweets(self, target:dict):
        with open('twitter_api.json', 'r', encoding='utf8') as f:
            jdata = json.load(f)
            f.close()
        username = target['username']
        select=" `created_at`"
        where=" `username` = '" + username + "' "
        latest = self.loadDataList(select=select, where=where)
        if (DEBUG): 
            print(latest)
            if (len(latest) != 0):
                print("latest= ", latest[0]['created_at'].strftime('%Y-%m-%d %H:%M:%S'))
            else:
                print("latest= None")

        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow() - timedelta(seconds=15)
        if (len(latest) != 0):
            start_time = max(latest[0]['created_at'], start_time)
        # set time, assume both of them is utc time
        start_time = start_time.isoformat('T') + 'Z'
        end_time = end_time.isoformat('T') + 'Z'
        # set for request
        url = "https://api.twitter.com/2/tweets/search/recent?"+\
            "tweet.fields=attachments,created_at,entities"+\
            "&max_results=50"+\
            "&expansions=author_id,in_reply_to_user_id"+\
            "&media.fields=&user.fields="+\
            f"&query=(from:{target['username']})"+\
            f"&start_time={start_time}&end_time={end_time}"
        payload = jdata['payload']
        headers= jdata['headers']

        # deal with error
        for i in range(5):
            try:
                res = requests.request("GET", url, headers=headers, data = payload)
            except Exception as e:
                print("Except: ", e, "status_code: ", res.status_code, "count: ", count, file=sys.stderr)
                print("url=\t", url)
                count += 1
                time.sleep(1)

            if res.status_code == requests.codes.ok:
                break
            else:
                print("FAIL to request, res.status_code=", res.status_code)
                print("url=\t", url)
            time.sleep(5)
        return res
    def insertTweet(self, tweets, username):
        for i in range(tweets['meta']['result_count']):
            data = tweets['data'][i]

            tweet_url = t_url + username + '/status/' + data['id']
            created_at = data['created_at'].replace("T"," ")[:-1]
            # deal with database
            db = pymysql.connect(host=HOST, user=USER, password=PW, db=DB,
                    cursorclass=pymysql.cursors.DictCursor)
            sql = "SELECT `id` FROM `tweets` WHERE `id`='"+str(data['id'])+"'"
            cur = db.cursor()
            is_found = cur.execute(sql)
            if (is_found):
                if (DEBUG): print(data['id'], "already saved to db")
                continue
            else:
                id = None
                if ('entities' in data.keys()):
                    if ('urls' in data['entities'].keys()):
                        for item in data['entities']['urls']:
                            if ("youtu.be/" in item['expanded_url']):
                                id= item['expanded_url'].split("youtu.be/")[-1]
                                if (DEBUG): print("id detect: ", id)
                if (id==None):
                    id = "NULL" 
                else:
                    # check youtube video information
                    res = youtubeAPI.Videos(id)
                    item = res['items'][0]
                    channelId = item['snippet']['channelId']
                    title = item['snippet']['title']
                    channelTitle = item['snippet']['channelTitle']
                    
                    sStartTime = aStartTime = aEndTime = "NULL"
                    print("parsing item: ", json.dumps(item, ensure_ascii=False, indent=4))
                    print(item.keys())
                    if ('liveStreamingDetails' in item.keys()):
                        liveSD = item['liveStreamingDetails']
                        if ('scheduledStartTime' in liveSD.keys()):
                            sStartTime = isoparse(liveSD['scheduledStartTime']).strftime('%Y-%m-%d %H:%M:%S')
                        if ('actualStartTime' in liveSD.keys()):
                            aStartTime = isoparse(liveSD['actualStartTime']).strftime('%Y-%m-%d %H:%M:%S')
                        if ('actualEndTime' in liveSD.keys()):
                            aEndTime = isoparse(liveSD['actualEndTime']).strftime('%Y-%m-%d %H:%M:%S')
                        sql = "INSERT IGNORE INTO `videos` ("+\
                            "`videoId`, `channel`, `isLiveStreaming`, `isForwarded`, `title`,"+\
                            " `scheduledStartTime`, `actualStartTime`, `actualEndTime`)"
                        sql += f"VALUES ('{id}', '{channelId}', '0', '0', '{title}', "+\
                                f" CAST('{sStartTime}' AS datetime), CAST('{aStartTime}' AS datetime), CAST('{aEndTime}' AS datetime))"
                    print(sql)
                    try:
                        cur.execute(sql)
                    except Exception as e:
                        time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        print(time+"\t[Error] \twhile adding video to db, sql:")
                        print(sql)
                    db.commit()
                sql = "INSERT IGNORE INTO `tweets` (`username`, `created_at`, `text`, `id`, `author_id`, `yt_videoid`) "
                sql += f"VALUES ('{username}', '{created_at}', '{data['text']}', '{data['id']}', '{data['author_id']}', '{id}')"
                try:
                    cur.execute(sql)
                except Exception as e:
                    time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    print(time+"\t[Error] \twhile adding tweet to db:")
                    print(sql)
                db.commit()
                if (DEBUG): print("commit")
            db.close()
    def setForwardedTweet(self, tweetId):
        self.connectDB()
        sql = f"UPDATE `propro_guild`.`tweets` SET `isForwarded`='1' WHERE  `id`='{tweetId}';"
        self.cur.execute(sql)
        self.db.commit()
def main():
    tracker = twitterTracker()
    for tg in tracker.TARGETS:
        if (DEBUG): print("dealing with username:\t", tg['username'])
        res = tracker.get_tweets(tg)
        
        if (res.status_code!=200): 
            print(f"fail to get_tweets from {tg['username']}")
            continue
        tweets = res.json()
        #print(json.dumps(tweets, ensure_ascii=False, indent=4))
        tracker.insertTweet(tweets, tg['username'])
        time.sleep(1)
if __name__ == "__main__":
    main()