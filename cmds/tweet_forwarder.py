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
        
        async def interval():
            await self.default_setting(bot)
            while not self.bot.is_closed():
                self.new_t_all = int(0)     # all new tweet number
                self.new_t_vis = int(0)
                self.count += 1
                now = dt.datetime.now()

                # report update time
                content=self.status_content + f"\n```{now.strftime('%Y/%m/%d %H:%M')}```"
                await self.msg_status.edit(content=content)
                #await self.ch_status.edit(name=f"Twi {now.strftime('%H:%M')} ✅")


                # set search time
                self.cur_st_t = self.last_ed_t
                self.cur_ed_t = dt.datetime.utcnow() + dt.timedelta(seconds=-15)
                # get embed message and send to speticular channel
                for tg in self.TARGETS:
                    self.channel = self.bot.get_channel(int(tg['twi_fw_ch']))
                    role = self.guild.get_role(int(tg['dc_role']))
                    

                    res = await self.get_tweets(tg, self.cur_st_t, self.cur_ed_t)
                    await asyncio.sleep(1) 
                    if (res.status_code!=200): 
                        print(f"fail to get_tweets from {tg['username']}")
                        continue
                    tweets = res.json()
                    
                    await self.parse_twitter_result(tweets, tg, role)
                    
                    await asyncio.sleep(1)

                # update last search range by current search range
                self.last_st_t = self.cur_st_t
                self.last_ed_t = self.cur_ed_t
                
                # print how many tweet are detect
                debug_msg = "{} -> {}, TwitterForwarderGen2 detect new tweet: {}, visible forward: {}".format(
                    self.cur_st_t, self.cur_ed_t, self.new_t_all, self.new_t_vis)
                if (self.new_t_all!=0): print(debug_msg)


                # wait
                await asyncio.sleep(SLEEP_TIME) # unit: second
        self.bg_task = self.bot.loop.create_task(interval())

    async def default_setting(self, bot):
        await bot.wait_until_ready()

        self.guild =  bot.get_guild(782232756238549032)
        print("TweetForwarder: working at guild=", self.guild)
        self.debug_ch = self.bot.get_channel(782232918512107542)
        
        self.channel = self.bot.get_channel(twitter_setting['dc_ch_id_general']) #default channel
        self.reply_ch = self.bot.get_channel(twitter_setting['dc_ch_id_reply'])
        self.ch_status = self.bot.get_channel(832496669752819743)

        if DEBUG:
            self.channel = self.debug_ch
            self.reply_ch = self.debug_ch

        self.last_st_t = dt.datetime.utcnow()
        self.last_ed_t = dt.datetime.utcnow() + dt.timedelta(hours=-DEBUG_HOUR,  seconds=-SLEEP_TIME*5)
        self.cur_st_t = dt.datetime.utcnow() 
        self.cur_ed_t = dt.datetime.utcnow()
        self.count = int(0)

        # for report update
        self.report_ch = self.bot.get_channel(814226297931694101)
        self.msg_status = await self.report_ch.fetch_message(829113456195797092)
        self.status_content = "**Tweet forwarder update at:**"


    async def get_tweets(self, target:dict, start_t, end_t):
        with open('twitter_api.json', 'r', encoding='utf8') as f:
            jdata = json.load(f)
            f.close()
        # set time, assume both of them is utc time
        await asyncio.sleep(0.1)
        start_time = start_t.isoformat('T') + 'Z'
        end_time = end_t.isoformat('T') + 'Z'
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
                count += 1
                await asyncio.sleep(5)

            if res.status_code == requests.codes.ok:
                break
            else:
                print("FAIL to request, res.status_code=", res.status_code)
            await asyncio.sleep(5)
        
        if res.status_code != requests.codes.ok:
            print("request fail, status_code: ", res.status_code)
            print("res.content: ", res.content)
            print("get_tweets : url=", url)
            await self.debug_ch.send(f"request fail, status_code: {res.status_code}" )
            await self.debug_ch.send(f"get_tweets : url={url}")
        
        return res
    async def parse_twitter_result(self, tweets, target, role):
        tg = target
        for i in range(tweets['meta']['result_count']):
            data = tweets['data'][i]

            tweet_url = t_url + tg['username'] + '/status/' + data['id']
            created_at = data['created_at'].replace("T"," ")[:-1]
            # deal with database
            db = pymysql.connect(host=HOST, user=USER, password=PW, db=DB,
                    cursorclass=pymysql.cursors.DictCursor)
            sql = "SELECT `id` FROM `tweets` WHERE `id`='"+str(data['id'])+"'"
            cur = db.cursor()
            is_found = cur.execute(sql)
            if (is_found):
                print(data['id'], "already saved to db")
                continue
            else:
                id = None
                if ('entities' in data.keys()):
                    if ('urls' in data['entities'].keys()):
                        for item in data['entities']['urls']:
                            if ("youtu.be/" in item['expanded_url']):
                                id= item['expanded_url'].split("youtu.be/")[-1]
                                print("id detect: ", id)
                if (id==None):
                    id = "NULL" 
                else:
                    # check youtube video information
                    res = youtubeAPI.Videos(id)
                    if (res['pageInfo']['totalResults']!=0):
                        item = res['items'][0]
                        channelId = item['snippet']['channelId']
                        title = item['snippet']['title']
                        channelTitle = item['snippet']['channelTitle']
                    else:
                        time = dt.datetime.now()
                        time = time.strftime('%Y-%m-%d %H:%M:%S')
                        print(time+"api request doesn't have result, videoId: "+id)
                        continue
                    
                    sStartTime = aStartTime = aEndTime = "NULL"
                    liveSD = item['liveStreamingDetails']
                    if ('scheduledStartTime' in liveSD.keys()):
                        sStartTime = isoparse(liveSD['scheduledStartTime']).strftime('%Y-%m-%d %H:%M:%S')
                    if ('actualStartTime' in liveSD.keys()):
                        aStartTime = isoparse(liveSD['actualStartTime']).strftime('%Y-%m-%d %H:%M:%S')
                    if ('actualEndTime' in liveSD.keys()):
                        aEndTime = isoparse(liveSD['actualEndTime']).strftime('%Y-%m-%d %H:%M:%S')

                    title = title.replace("'","'"*2)
                    sql = "INSERT IGNORE INTO `videos` ("+\
                        "`videoId`, `channel`, `isForwarded`, `title`,"+\
                        " `scheduledStartTime`, `actualStartTime`, `actualEndTime`)"
                    sql += f"VALUES ('{id}', '{channelId}', '0', '{title}', "+\
                           f" CAST('{sStartTime}' AS datetime), CAST('{aStartTime}' AS datetime), CAST('{aEndTime}' AS datetime))"
                    print(sql)
                    try:
                        cur.execute(sql)
                    except Exception as e:
                        print(e)
                        print("sql=", sql)
                        raise e
                    db.commit()
                text = data['text'].replace("'", "'"*2)
                sql = "INSERT IGNORE INTO `tweets` (`username`, `created_at`, `text`, `id`, `author_id`, `yt_videoid`) "
                sql += f"VALUES ('{tg['username']}', '{created_at}', '{text}', '{data['id']}', '{data['author_id']}', '{id}')"
                try:
                    cur.execute(sql)
                except Exception as e:
                    print(e)
                    print("sql=", sql)
                    raise e

                db.commit()
                print("commit")
            db.close()
            # deal with tweet
            # found tweet by target[username], and get tweet url=twitter_url+target['username']+'/status/'+tweet_id
            
            try:
                created_at = dt.datetime.fromisoformat(created_at)
            except Exception as e:
                print("Exception in tweet time transform: ", e, file=sys.stderr)
                created_at = dt.datetime.now()
            
            self.new_t_all += 1
            msg_mention = f"{role.mention} "
            msg_S = f"{tg['nickname']} "
            msg_V = ""
            msg_O = ""
            msg_Link = f"\n{tweet_url}"
            debug_msg = f'{tg["username"]} '
            
            # tweet in reply to user
            await asyncio.sleep(0.2)
            if "in_reply_to_user_id" in data.keys():
                
                msg_V = "just reply a data:"
                debug_msg += f'reply to id: {data["in_reply_to_user_id"]}, '
                if (not (data["in_reply_to_user_id"] in BOX_MEMBER_ID)):
                    debug_msg += f'message forward to {self.reply_ch.name}'
                    if (DEBUG):
                        await self.debug_ch.send(msg_S + msg_V + msg_O + msg_Link)
                    else:
                        await self.reply_ch.send(msg_S + msg_V + msg_O + msg_Link)
                    print(debug_msg)
                else:
                    msg_V = "tete!"
                    if (data["in_reply_to_user_id"] == tg["username"]):
                        msg_V = "reply to herself"
                    debug_msg += f'is relative, message forward to {self.channel.name}'
                    if (DEBUG):
                        await self.debug_ch.send(msg_S + msg_V + msg_O + msg_Link)
                    else:
                        await self.channel.send(msg_S + msg_V + msg_O + msg_Link)
                    print(debug_msg)
            elif (data["text"][:2] == "RT"):
                msg_V = "just RT this:"
                debug_msg += f'RT, message forward to {self.channel.name}'
                if (DEBUG):
                    await self.debug_ch.send(msg_mention + msg_S + msg_V + msg_O + msg_Link)
                else:
                    await self.channel.send(msg_mention + msg_S + msg_V + msg_O + msg_Link)
                print(debug_msg)
            else:

                # visiable forward to channel
                self.new_t_vis += 1
                msg_V = "just post a tweet:"
                debug_msg += f'post a tweet, message forward to {tg["twi_fw_ch"]}'
                if (DEBUG):
                    await self.debug_ch.send(msg_mention + msg_S + msg_V + msg_O + msg_Link)
                else:
                    await self.bot.get_channel(int(tg['twi_fw_ch'])).send(
                        msg_mention + msg_S + msg_V + msg_O + msg_Link)
                print(debug_msg)
def setup(bot):
    bot.add_cog(TweetForwarder(bot))
