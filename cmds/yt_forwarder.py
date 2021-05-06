# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from core.classes import Cog_Extension
import os, json, asyncio, pymysql.cursors
from datetime import datetime, timedelta
import traceback, sys
import dateutil.parser

# my module
import ytTracker
with open('yt_fw_setting.json','r', encoding='utf8') as f:
    yt_fw_setting = json.load(f)
    f.close()
y_url = "https://youtu.be/"
class  ytForwarder(Cog_Extension):
    def isVideo(self, videoInfo):
        boolean =   videoInfo['scheduledStartTime']==None and\
                    videoInfo['channelId']!=None
        return True if boolean else False
            
    def isLive(self, videoInfo):
        boolean =   videoInfo['actualStartTime']!=None and\
                    videoInfo['actualEndTime']==None
        return True if boolean else False

    @commands.command()
    async def yt_forwarder_loop_count(self, ctx):
        msg = f"YouTube Forwarder loop counts: {self.count}"
        print("Command response: ", msg)
        await ctx.send(msg)

    def __init__(self, bot):
        self.bot = bot
        self.count = 0
        self.tracker = ytTracker.ytTracker()
        async def interval():
            async def forwardMsg(result):
                if (len(result)==0): return
                for item in result:
                    # forward videos
                    ## get information

                    if (item['channelId']==""): continue

                    targetInfo = yt_fw_setting[item['channelId']]
                    print("getting role: " +targetInfo['dc_role'])
                    role = self.guild.get_role(int(targetInfo['dc_role']))
                    print("get role=", str(role))
                    channel = self.bot.get_channel(int(targetInfo['yt_fw_ch']))
                    nickname = targetInfo['nickname']

                    print("video type: ", self.isVideo(item),self.isLive(item) )
                    print(item)
                    if (self.isVideo(item)):
                        print("is video")
                        content = f"{role.mention} {nickname} 發布了影片：{item['title']}\n"
                        content += y_url+item['videoId']
                        await channel.send(content)
                    elif (self.isLive(item)):
                        print("is stream")
                        content = f"{role.mention} {nickname} 開始直播了：{item['title']}\n"
                        content += y_url+item['videoId']
                        await channel.send(content)

                    self.tracker.setForwardedVideo(item['videoId'])
                    print(f"set video {item['videoId']}to isForwarded")


            await bot.wait_until_ready()
            self.guild =  bot.get_guild(782232756238549032)
            SLEEP_TIME = 15 # 15 seconds
            tracker = self.tracker

            while not self.bot.is_closed():
                self.count += 1
                now = datetime.now()
                
                
                res = tracker.loadDataList(select="*",
                    request_forward_List=True)
                print(now.strftime('%Y-%m-%d %H:%M:%S')+" yt_forwarder dealing with: ", res)
                await forwardMsg(res)

                await asyncio.sleep(SLEEP_TIME)

        self.bg_task = self.bot.loop.create_task(interval())
def setup(bot):
    bot.add_cog(ytForwarder(bot))
