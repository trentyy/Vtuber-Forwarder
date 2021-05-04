import discord
import datetime as dt
from discord.ext import commands
from core.classes import Cog_Extension


class Main(Cog_Extension):
    @commands.command()
    async def ping(self, ctx):
        await ctx.send(f'{round(self.bot.latency*1000)} (ms)')
    @commands.command()
    async def botsay(self, ctx, target_ch_id, *, msg):
        print(ctx.author.roles)
        target_ch = self.bot.get_channel(int(target_ch_id))
        if (ctx.guild.get_role(785503910818218025) in ctx.author.roles):
            await ctx.message.delete()
            await target_ch.send(msg)
        else:
            await ctx.send("你誰啊?")
    @commands.command()
    async def curtime(self, ctx):
        await ctx.send(dt.datetime.now())

def setup(bot):
    bot.add_cog(Main(bot))