"""
use youtube api to update propro member's streaming data

"""

import os, json, time, pymysql.cursors
from datetime import datetime, timedelta
import traceback, sys
from dateutil.parser import isoparse

import googleapiclient.discovery

# my module
from APIs import youtubeAPI

with open('db_setting.json', 'r') as f:
    db_setting = json.load(f)
    f.close()
HOST = db_setting['host']
USER = db_setting['user']
PW = db_setting['password']
DB = db_setting['database']

class ytUpdater():
    def __init__(self):
        with open('db_setting.json', 'r') as f:
            db_setting = json.load(f)
            f.close()

    def connectDB(self, host=HOST, user=USER,
                    password=PW, database=DB):
        self.db = pymysql.connect(
            host=host, user=user, password=password, db=database,
            cursorclass=pymysql.cursors.DictCursor)
        self.cur = self.db.cursor()
    def closeDB(self):
        self.db.close()
    def task(self, do_times, sleep_seconds, doSearchList=True):
        self.connectDB()
        if (doSearchList):
            res = youtubeAPI.SearchList()
            videos=[]
            for item in res['items']:
                videoId, snippet = item['id']['videoId'], item['snippet']
                channelId, title = snippet['channelId'], snippet['title']
                liveBroadcastContent = snippet['liveBroadcastContent']
                videos.append(videoId)
            print("videos in task, searchlist: ", videos)
            self.insertVideo(videos)
        
        for i in range(do_times):
            # load target video list from database
            db_videos = self.loadDataList()
            
            # update these video with youtube api
            self.updateVideoStatus(db_videos)
            
            # sleep and wait for next run
            time.sleep(sleep_seconds)
        # finish task successfully
        self.closeDB()
    def loadDataList(self, select="videoId", type="waiting"):
        # type: waiting, live, completed
        sql = f"SELECT {select} FROM `videos` WHERE `isForwarded` = 0 AND "
        if (type=="waiting"):
            sql += "(`actualStartTime` IS NULL OR `actualEndTime` IS NULL);"
        elif (type=="live"):
            sql += "(`actualStartTime` IS NOT NULL OR `actualEndTime` IS NULL);"
        elif (type=="completed"):
            sql += "(`actualStartTime` IS NOT NULL OR `actualEndTime` IS NOT NULL);"
        else:
            print("type is not in [waiting, live, completed]")
            sql += "(`actualStartTime` IS NULL OR `actualEndTime` IS NULL);"
        result_num = self.cur.execute(sql)
        result = self.cur.fetchall()
        return result
    def parseVideoInfo(self, request):
        try:
            item = request['items'][0]  # deal with yt video api
        except Exception as e:
            print(e)
            print(request)
        channelId = item['snippet']['channelId']
        title = item['snippet']['title']
        channelTitle = item['snippet']['channelTitle']
        
        sStartTime = aStartTime = aEndTime = "NULL"
        liveSD = item['liveStreamingDetails']
        if ('scheduledStartTime' in liveSD.keys()):
            sStartTime = isoparse(liveSD['scheduledStartTime'])
            sStartTime = "'"+sStartTime.strftime('%Y-%m-%d %H:%M:%S')+"'"
        if ('actualStartTime' in liveSD.keys()):
            aStartTime = isoparse(liveSD['actualStartTime'])
            aStartTime = "'"+aStartTime.strftime('%Y-%m-%d %H:%M:%S')+"'"
        if ('actualEndTime' in liveSD.keys()):
            aEndTime = isoparse(liveSD['actualEndTime'])
            aEndTime = "'"+aEndTime.strftime('%Y-%m-%d %H:%M:%S')+"'"
        return channelId, title, sStartTime, aStartTime, aEndTime
    def updateVideoStatus(self, result):
        # videoIds is a list of youtube videoId, use it with api to update
        print("updating these video: ", rsult)
        for item in result:
            videoId = item['videoId']
            request = youtubeAPI.Videos(
                videoId,
                part="snippet,liveStreamingDetails"
            )
            output = self.parseVideoInfo(request)
            channelId, title, sStartTime, aStartTime, aEndTime = output
            
            sql =   "UPDATE `videos` SET `scheduledStartTime` = " + sStartTime
            sql +=  ", `actualStartTime` = " + aStartTime
            sql +=  ", `actualEndTime` = " + aEndTime
            sql += " WHERE `videos`.`videoId` = " + "'"+videoId+"'"
            self.cur.execute(sql)
            self.db.commit()
    def insertVideo(self, videoIds):
        for videoId in videoIds:
            request = youtubeAPI.Videos(
                videoId,
                part="snippet,liveStreamingDetails"
            )

            output = self.parseVideoInfo(request)
            channelId, title, sStartTime, aStartTime, aEndTime = output

            if ("'" in title):
                title = title.replace("'", "'"*2)
            sql =   "INSERT IGNORE INTO `videos` ("+\
                    "`videoId`, `channel`, `isForwarded`, `title`,"+\
                    " `scheduledStartTime`, `actualStartTime`, `actualEndTime`)"
            sql +=  f"VALUES ('{videoId}', '{channelId}', '0', '{title}', "+\
                    f" CAST({sStartTime} AS datetime), CAST({aStartTime} AS datetime), CAST({aEndTime} AS datetime))"
            try:
                self.cur.execute(sql)
            except pymysql.err.ProgrammingError as e:
                print(e)
                print(sql)
                raise e
            self.db.commit()
if __name__ == "__main__":
    updater = ytUpdater()
    print(updater.loadDataList(select="videoId, scheduledStartTime", type="waiting"))
    updater.task(do_times=2, sleep_seconds=10, doSerachList=False)

    