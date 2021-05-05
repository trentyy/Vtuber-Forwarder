# -*- coding: utf-8 -*-
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

DEBUG = False

with open('db_setting.json', 'r') as f:
    db_setting = json.load(f,encoding='utf-8')
    f.close()
HOST = db_setting['host']
USER = db_setting['user']
PW = db_setting['password']
DB = db_setting['database']
with open('yt_fw_setting.json', 'r',encoding='utf-8') as f:
    yt_setting = json.load(f)
    f.close()
BOX_MEMBER_ID = yt_setting['BOX_MEMBER_ID']
class ytTracker():
    def __init__(self):
        self.connectDB()

    def connectDB(self, host=HOST, user=USER,
                    password=PW, database=DB):
        self.db = pymysql.connect(
            host=host, user=user, password=password, db=database,
            cursorclass=pymysql.cursors.DictCursor)
        self.cur = self.db.cursor()
    def closeDB(self):
        return self.db.close()

    def task(self, do_times, sleep_seconds, doSearchList=True):
        self.connectDB()
        if (doSearchList):
            res = youtubeAPI.SearchList()
            videos=[]
            for item in res['items']:
                videoId, snippet = item['id']['videoId'], item['snippet']
                channelId, title, publishedAt = snippet['channelId'], snippet['title'], snippet['publishedAt']
                liveBroadcastContent = snippet['liveBroadcastContent']
                videos.append(videoId)
            if DEBUG: print("videos in task, searchlist: ", videos)
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
    def loadDataList(self, select="videoId", stream_type="waiting", request_forward_List=False):
        # stream_type: waiting, live, completed
        self.connectDB()
        sql = f"SELECT {select} FROM `videos` WHERE `isForwarded` = 0 AND "
        if request_forward_List:
            sql += "(`scheduledStartTime` IS NULL OR (`actualStartTime` IS NOT NULL AND `actualEndTime` IS NULL));"
        else:
            if (stream_type=="waiting"):
                sql += "`scheduledStartTime` IS NOT NULL AND "
                sql += "(`actualStartTime` IS NULL OR `actualEndTime` IS NULL);"
            elif (stream_type=="live"):
                sql += "`scheduledStartTime` IS NOT NULL AND "
                sql += "(`actualStartTime` IS NOT NULL AND `actualEndTime` IS NULL);"
            elif (stream_type=="completed"):
                sql += "`scheduledStartTime` IS NOT NULL AND "
                sql += "(`actualStartTime` IS NOT NULL AND `actualEndTime` IS NOT NULL);"
            else:
                print("stream_type is not in [waiting, live, completed]")
                sql += "(`actualStartTime` IS NULL OR `actualEndTime` IS NULL);"
        try:
            result_num = self.cur.execute(sql)
            result = self.cur.fetchall()
        except Exception as e:
            time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(time+"\t[Error] \tytTracker.loadDataList while execute sql:")
            print(sql)
            raise e
        self.closeDB()
        return result
    def parseVideoInfo(self, request):
        try:
            item = request['items'][0]  # deal with yt video api
        except Exception as e:
            print(datetime.now(), e)
            print(request)
            return None
        res = {}
        channelId = item['snippet']['channelId']
        title = item['snippet']['title']
        channelTitle = item['snippet']['channelTitle']
        publishedAt = isoparse(item['snippet']['publishedAt'])
        sStartTime = aStartTime = aEndTime = "NULL"

        res['channelId'] = channelId
        res['title'] = title
        res['publishedAt'] = "'"+publishedAt.strftime('%Y-%m-%d %H:%M:%S')+"'"
        res['scheduledStartTime'] = "NULL"
        res['actualStartTime'] = "NULL"
        res['actualEndTime'] = "NULL"

        if ('liveStreamingDetails' in item.keys()):
            liveSD = item['liveStreamingDetails']
            if ('scheduledStartTime' in liveSD.keys()):
                sStartTime = isoparse(liveSD['scheduledStartTime'])
                sStartTime = "'"+sStartTime.strftime('%Y-%m-%d %H:%M:%S')+"'"
                res['scheduledStartTime'] = sStartTime
            if ('actualStartTime' in liveSD.keys()):
                aStartTime = isoparse(liveSD['actualStartTime'])
                aStartTime = "'"+aStartTime.strftime('%Y-%m-%d %H:%M:%S')+"'"
                res['actualStartTime'] = aStartTime
            if ('actualEndTime' in liveSD.keys()):
                aEndTime = isoparse(liveSD['actualEndTime'])
                aEndTime = "'"+aEndTime.strftime('%Y-%m-%d %H:%M:%S')+"'"
                res['actualEndTime'] = aEndTime
        return res
    def updateVideoStatus(self, result):
        # videoIds is a list of youtube videoId, use it with api to update
        self.connectDB()
        if DEBUG: print("updating these video: ", result)
        for item in result:
            videoId = item['videoId']
            res = youtubeAPI.Videos(
                videoId,
                part="snippet,liveStreamingDetails"
            )
            if res['pageInfo']['totalResults']==0:
                time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(time+"\tPASS\tCan't find video id: ",videoId)
                continue
            res = self.parseVideoInfo(res)
            
            sql =   "UPDATE `videos` SET "
            sql += " `publishedAt` = " + res['publishedAt']
            sql += ", `scheduledStartTime` = " + res['scheduledStartTime']
            sql += ", `actualStartTime` = " + res['actualStartTime']
            sql += ", `actualEndTime` = " + res['actualEndTime']
            sql += " WHERE `videos`.`videoId` = " + "'"+videoId+"'"
            self.cur.execute(sql)
            self.db.commit()
        self.closeDB()
    def insertVideo(self, videoIds):
        self.connectDB()
        for videoId in videoIds:
            request = youtubeAPI.Videos(
                videoId,
                part="snippet,liveStreamingDetails"
            )
            if request['pageInfo']['totalResults']==0:
                time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(time+"\tPASS\tCan't find video id: ",videoId)
                continue
            res = self.parseVideoInfo(request)
            if (res['channelId'] not in BOX_MEMBER_ID.values()):
                time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(time+"\tPASS\tNot publish by members, video id: ",videoId)
                continue
            sStartTime = res['scheduledStartTime']
            aStartTime = res['actualStartTime']
            aEndTime = res['actualEndTime']
            if ("'" in res['title']):
                res['title'] = res['title'].replace("'", "'"*2)
            sql =   "INSERT IGNORE INTO `videos` ("+\
                    "`videoId`, `channel`, `isForwarded`, `title`,"+\
                    " `publishedAt`,"+\
                    " `scheduledStartTime`, `actualStartTime`, `actualEndTime`)"
            sql +=  f"VALUES ('{videoId}', '{res['channelId']}', '0', '{res['title']}', "+\
                    f" CAST({res['publishedAt']} AS datetime), "+\
                    f" CAST({sStartTime} AS datetime), CAST({aStartTime} AS datetime), CAST({aEndTime} AS datetime))"
            try:
                self.cur.execute(sql)
            except pymysql.err.ProgrammingError as e:
                print(e)
                print(sql)
                self.connectDB()
            self.db.commit()
        self.closeDB()
    def setForwardedVideo(self, videoId):
        self.connectDB()
        sql = f"UPDATE `propro_guild`.`videos` SET `isForwarded`='1' WHERE  `videoId`='{videoId}';"
        self.cur.execute(sql)
        self.db.commit()
        self.closeDB()
def main():
    tracker = ytTracker()
    res = tracker.loadDataList(select="*", request_forward_List=True)
    
    tracker.updateVideoStatus(res)
    if DEBUG:
        print(type(res), len(res))
        print(res)
    tracker.task(do_times=29, sleep_seconds=60, doSearchList=True)
if __name__ == "__main__":
    main()
    