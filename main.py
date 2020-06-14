import os
import json
import discord
from discord.ext import commands
from discord.ext.commands import MemberConverter


# -> Definitions
# ---------------------

with open("config-local.json") as f:
    configFile = json.load(f)

prefix = '__'
bot = commands.Bot(command_prefix=(prefix, ), case_insensitive=True)
botToken = configFile['testerToken']

def is_bot(m):
    return m.author == bot.user or m.content[0] == prefix

def is_bot_owner(ctx):
    return ctx.message.author.id ==  168437285908512768

def check(author):
    def inner_check(message):
        return message.author == author
    return inner_check

@bot.event
async def on_ready():
    print('Bot ready!')
    game = discord.Game("for science!")
    await bot.change_presence(activity=game)

# -> Comandos          
# ---------------------

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! {round(bot.latency*1000)}ms")

@bot.command()
@commands.check(is_bot_owner)
async def load(ctx, extension):
    bot.load_extension(f'cogs.{extension}')
    await ctx.send(f'{extension} cargada!')

@bot.command()
@commands.check(is_bot_owner)
async def unload(ctx, extension):
    bot.unload_extension(f'cogs.{extension}')
    await ctx.send(f'{extension} descargada!')

@bot.command()
@commands.check(is_bot_owner)
async def reload(ctx, extension):
    if extension == 'all':
        for filename in os.listdir('./cogs'):
            bot.unload_extension(f'cogs.{filename[:-3]}')
            bot.load_extension(f'cogs.{filename[:-3]}')
        await ctx.send('Cogs recargadas!')
        return
    bot.unload_extension(f'cogs.{extension}')
    bot.load_extension(f'cogs.{extension}')
    await ctx.send(f'{extension} recargada!')


# -> Run
# ---------------------

for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):  # Checkeo que sean .py
        # Cargo el archivo, es necesario solo usar el nombre, sin la extensión .py
        bot.load_extension(f'cogs.{filename[:-3]}')

bot.run(botToken)

