# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from core.classes import Cog_Extension
import json, asyncio, sys, socket
import requests, urllib3
import datetime as dt
from dateutil.parser import isoparse
import pymysql

# my module
from APIs import youtubeAPI
import ytTracker

DEBUG=False
DEBUG_HOUR=8
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
proproduction = twitter_setting['proproduction']
mikuru = twitter_setting['mikuru']
mia = twitter_setting['mia']
chiroru = twitter_setting['chiroru']
isumi = twitter_setting['isumi']
yuru = twitter_setting['yuru']
# gen2
mai = twitter_setting['mai']
rin = twitter_setting['rin']
aoi = twitter_setting['aoi']
momoa = twitter_setting['momoa']
azusa = twitter_setting['azusa']

BOX_MEMBER = (proproduction, 
        mikuru, mia, chiroru, isumi, yuru, 
        mai, rin, aoi, momoa)
TARGETS_GEN1 = mikuru, mia, chiroru, isumi, yuru
TARGETS_GEN2 = mai, rin, aoi, momoa, azusa      # here is TARGETS list
BOX_MEMBER_ID = [x['id'] for x in BOX_MEMBER]
SLEEP_TIME = 60

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
    async def set_start_time(self, ctx, time):
        try:
            self.last_ed_t = dt.datetime.fromisoformat(time)
            print("Start time set to: ", self.last_ed_t)
            await ctx.send(f"Start time set to: {self.last_ed_t}")
        except Exception as e:
            await ctx.send(e)
    def __init__(self, bot):
        self.bot = bot
        self.TARGETS = BOX_MEMBER
        self.count = 0
        self.twitterTracker = twitterTracker.twitterTracker()
        
        async def interval():
            async def forwardMsg(result, target):
                if (len(res)==0): return
                for item in result:
                    # forward tweets
                    ## get information
                    channel = self.bot.get_channel(int(tg['twi_fw_ch']))
                    role = self.guild.get_role(int(tg['dc_role']))
                    tweetId = tg['id']
                    username = item['username']
                    nickname = tg['nickname']
                    text = item['text']
                    tweet_url = t_url + username + "/status/" + tweetId

                    content = sname = motion = ""

                    if text[0] == '@':
                        sname = text.split(" ")[0] # subject name
                        motion = "標註了："
                        print("is quote")
                    elif text[:3] == "RT ":
                        sname = text[3:].split(":")[0] # subject name
                        motion = "轉推了："
                        print("is retweet")
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
                        

            await self.default_setting(bot)
            while not self.bot.is_closed():
                self.count += 1
                now = dt.datetime.now()

                # get embed message and send to speticular channel
                for tg in self.TARGETS:
                    res = self.twitterTracker.loadDataList(
                        select = " * ",
                        where = "`isForwarded` = 0 AND `username` = " + tg['username'],
                        extra = " ORDER BY `created_at` ASC LIMIT 5"
                    )
                    await forwardMsg(res, tg)
                    await asyncio.sleep(0.2)

                # wait
                await asyncio.sleep(SLEEP_TIME) # unit: second
        self.bg_task = self.bot.loop.create_task(interval())

    async def default_setting(self, bot):
        await bot.wait_until_ready()

        self.guild =  bot.get_guild(782232756238549032)
        print("TweetForwarder: working at guild=", self.guild)
        self.debug_ch = self.bot.get_channel(782232918512107542)
        
        self.reply_ch = self.bot.get_channel(twitter_setting['dc_ch_id_reply'])

        if DEBUG:
            self.reply_ch = self.debug_ch

def setup(bot):
    bot.add_cog(TweetForwarder(bot))
