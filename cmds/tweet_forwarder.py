# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from core.classes import Cog_Extension
import json, asyncio, sys, socket
import requests, urllib3
from datetime import datetime, timedelta
from dateutil.parser import isoparse
import pymysql

# my module
from APIs import youtubeAPI
import twitterTracker

DEBUG=False
DEBUG_HOUR=0
if DEBUG: DEBUG_HOUR=3

# load data and set variables
with open('twitter_forward_setting.json','r', encoding='utf8') as f:
    twitter_setting = json.load(f)
    f.close()
t_url = twitter_setting['twitter_url']
twitter_icon_url = twitter_setting['twitter_icon_url']

with open('db_setting.json', 'r') as f:
    db_setting = json.load(f)
    f.close()
HOST=db_setting['host']
USER=db_setting['user']
PW=db_setting['password']
DB=db_setting['database']
# gen1 with staff
proproduction = twitter_setting['_proproduction']
mikuru = twitter_setting['kadukimikuru']
mia = twitter_setting['yumesakimia']
chiroru = twitter_setting['amachiroru']
isumi = twitter_setting['sakuraisumi']
yuru = twitter_setting['umitukiyuru']
# gen2
mai = twitter_setting['koinoya_mai']
rin = twitter_setting['hanakumo_rin']
aoi = twitter_setting['shiroseaoi']
momoa = twitter_setting['ikoimomoa']
azusa = twitter_setting['sakuya_azusa']

BOX_MEMBER = (proproduction, 
        mikuru, mia, chiroru, isumi, yuru, 
        mai, rin, aoi, momoa, azusa)
TARGETS_GEN1 = mikuru, mia, chiroru, isumi, yuru
TARGETS_GEN2 = mai, rin, aoi, momoa, azusa      # here is TARGETS list
BOX_MEMBER_ID = [x['id'] for x in BOX_MEMBER]
SLEEP_TIME = 15

with open('twitter_api.json', mode='r', encoding='utf8') as jfile:
    jdata = json.load(jfile)

class TweetForwarder(Cog_Extension):
    @commands.command()
    async def set_target(self, ctx, msg):
        if ("all" in msg):
            self.TARGETS = BOX_MEMBER
            await ctx.send('tweet_forwarder set target to all box member')
        elif ("gen1" in msg):
            self.TARGETS = TARGETS_GEN1
            await ctx.send('tweet_forwarder set target to gen1')
        elif ("gen2" in msg):
            self.TARGETS = TARGETS_GEN2
            await ctx.send('tweet_forwarder set target to gen2')
    @commands.command()
    async def tweet_forwarder_loop_count(self, ctx):
        msg = f"Tweet Forwarder loop counts : {self.count}"
        print("Command response: ", msg)
        await ctx.send(msg)
    def __init__(self, bot):
        self.bot = bot
        self.TARGETS = BOX_MEMBER
        self.count = 0
        self.tracker = twitterTracker.twitterTracker()
        twi_set = twitter_setting 
        async def interval():
            async def forwardMsg(result):
                if (len(res)==0): return
                try:
                    for item in result:
                        # forward tweets
                        ## get information
                        username = item['username']
                        print("username= ", username)
                        target = twi_set[username]
                        print("target= ", target)
                        channel = self.bot.get_channel(int(target['twi_fw_ch']))
                        role = self.guild.get_role(int(target['dc_role']))
                        tweetId = item['id']
                        nickname = target['nickname']
                        text = item['text']
                        tweet_url = t_url + username + "/status/" + str(tweetId)

                        content = sname = motion = ""

                        if text[0] == '@':
                            sname = text.split(" ")[0] # subject name
                            motion = "回覆了："
                            print("is quote")
                            content = f"{nickname}{motion}{sname}\n"
                            content += tweet_url
                            if (sname[1:] not in BOX_MEMBER_ID):
                                await self.reply_ch.send(content)
                            else:
                                await channel.send(content)
                        elif text[:3] == "RT ":
                            sname = text[3:].split(":")[0] # subject name
                            motion = "轉推了："
                            print("is retweet")
                            content = f"{role.mention}{nickname}{motion}{sname}\n"
                            content += tweet_url
                            await channel.send(content)
                        else:
                            motion = "tweet: "
                            print("is retweet")
                            content = f"{role.mention}{nickname}{motion}{sname}\n"
                            content += tweet_url
                            await channel.send(content)

                        try:
                            self.tracker.setForwardedTweet(tweetId)
                        except Exception as e:
                            print("Error when setForwardedTweet:", e)
                            raise(e)
                        await asyncio.sleep(0.2)
                except Exception as e:
                    print("Error when forwardMsg:", e)
                    msg = f"{self.developer_role.mention} Error tweet_forwarder when forwardMsg {e}"
                    await self.debug_ch.send(msg)
                    raise(a)
            await self.default_setting(bot)
            while not self.bot.is_closed():
                self.count += 1
                now = datetime.now()

                # get embed message and send to speticular channel
                res = self.tracker.loadDataList(
                    select = " * ",
                    where = "`isForwarded` = 0",
                    extra = " ORDER BY `created_at` ASC LIMIT 5"
                )
                print(now.strftime('%Y-%m-%d %H:%M:%S')+" twitter forwarder dealing with: ", res)
                await forwardMsg(res)

                # wait
                await asyncio.sleep(SLEEP_TIME) # unit: second
        self.bg_task = self.bot.loop.create_task(interval())

    async def default_setting(self, bot):
        await bot.wait_until_ready()

        self.guild =  bot.get_guild(782232756238549032)
        print("TweetForwarder: working at guild=", self.guild)
        self.debug_ch = self.bot.get_channel(782232918512107542)
        self.developer_role = self.guild.get_role(785503910818218025)
        
        self.reply_ch = self.bot.get_channel(twitter_setting['dc_ch_id_reply'])

        if DEBUG:
            self.reply_ch = self.debug_ch

def setup(bot):
    bot.add_cog(TweetForwarder(bot))
