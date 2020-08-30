from discord.ext import commands
import discord
import random
import re

# -> Global use variables
# -----------------------
dice = [str(i) for i in range(1,7)]
print(dice)


# -> Check functions
# ------------------
def check_author_channel(author, channel_id):
    def inner_check(message):
        return message.author == author and message.channel.id == channel_id
    return inner_check

def check_channel(channel_id):
    def inner_check(message):
        return message.channel.id == channel_id
    return inner_check

async def get_member_object(self,ctx,text):
    try:
        member_id = re.findall(r'<@!?(\d+)>',text)[0]
    except:
        return False
    member = ctx.guild.get_member(int(member_id))
    return member


# -> Game functions
# -----------------
async def get_players(self, ctx, channel_id):
    """
    Initialize a a player dictionary,
     then  ask for the players amount and iterate that amount of times asking for players,
     that will be added to the player dictionary.
     The players dictionary contains each player id as a key and their score as a value:
     {
     <id player1> : 0,
     <id player2> : 0
     }
    """
    players = dict()
    await ctx.send(f'<@{ctx.author.id}> Cuántos jugadores va a haber?')
    msj = await self.bot.wait_for('message',check=check_author_channel(ctx.author, channel_id))
    amount = int(msj.content)

    for i in range(amount):
        await ctx.send(f'Que el jugador {i+1} envíe un mensaje aquí')
        msj = await self.bot.wait_for('message', check=check_channel(channel_id))
        player = msj.author.id
        players[player] = 0

    await ctx.send('Los jugadores son:')
    for player in players:
        await ctx.send(f'<@{player}>')
    return players

async def initial_roll(self, channel_id, dices_amount):
    """
    Takes the amount of dices, roll each one and returns the values as a list
    """
    initial_rolls = []
    for roll in range(dices_amount):
        initial_rolls.append(random.choice(dice))
    return initial_rolls


async def get_score(self, rolls, score = 0):
    """
    Checkes the score, based on the rolls
    """
    # <TODO> Check if the triple values happened in the same roll
    triple_scores = {
            "1": 1000,
            "2": 200,
            "3": 300,
            "4": 400,
            "5": 500,
            "6": 600,
            }
    single_scores = {
            "1": 100,
            "5": 50
            }

    counts = dict()
    
    for roll in rolls:
        counts[roll] = rolls.count(roll)
    
    for key in counts:
        if counts[key] >= 3:
            score += triple_scores[key]
            counts[key] -= 3
        if key in single_scores:
            score += single_scores[key]*counts[key]
    
    return score

def can_discard(rolls):
    """
    Check if the user can discard dices
    """
    if ('1' in rolls) or ('5' in rolls) or (3 in [rolls.count(r) for r in rolls]):
        return True
    else: 
        return False

async def discard(self, ctx, channel_id, rolls, player):
    """ 
    From a list of rolls asks for the user wich valeus should be discarded,
     the imput must repeat the value if necesary.
     i.e.:

     initial roll: ['1','2','4,'4','1']
     to discard one 1 and the two 5s the input must be "144"
     (since it's regex a delimiter could be used)
    """
    dices_amount = len(rolls)
    player_member = await get_member_object(self, ctx, f'<@{player}>')
    await ctx.send('Qué dados deseas descartar?')
    msj = await self.bot.wait_for('message',check=check_author_channel(player_member, channel_id))

    discards = re.findall(r'\d',msj.content)

    for d in discards:
        rolls.remove(d)
    while len(rolls) < dices_amount:
        rolls.append(random.choice(dice))
    return rolls


class Diezmil(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(allias=['dm'])
    async def dm(self, ctx, dices_amount=5):
        channel_id = ctx.channel.id
        scores = await get_players(self, ctx, channel_id)

        while True:
            for player in scores:
                await ctx.send(f'Turno de <@{player}>:')
                await ctx.send('Tirando tus dados...')
                
                rolls = await initial_roll(self, channel_id, dices_amount)
                await ctx.send(f'Tus dados son: {rolls}')
                
                score = await get_score(self, rolls, 0) 
                await ctx.send(f'Estos rolls valen: {score}')

                while can_discard(rolls):
                    player_member = await get_member_object(self, ctx, f'<@{player}>')
                    await ctx.send('Deseas descartar? (y/n)')
                    msj = await self.bot.wait_for('message',check=check_author_channel(player_member, channel_id))
                    
                    if msj.content == 'y':
                        rolls = await discard(self, ctx, channel_id, rolls, player)
                        score = await get_score(self, rolls, 0) 
                        await ctx.send(f'<@{player}> Tus nuevos rolls son: {rolls} y valen {score} puntos')
                    elif msj.content == 'n':
                        break
                    else:
                        await ctx.send('Mensaje incorrecto, tiene que ser "y" o "n"')

                    if not can_discard(rolls):
                        await ctx.send('No puedes descartar dados')
        
                new_score = scores[player] + score
                # -> Start condition 
                if new_score < 750:
                    await ctx.send('Aún no puedes entrar al juego')
                # -> Check if score is above 10000
                elif new_score > 10000:
                    await ctx.send('Te pasaste de diez mil! Volvés a tu estado anterior')
                # -> Check win condition
                elif new_score == 10000:
                    await ctx.send(f'Felicitaciones! <@{player}>, ganaste al diez mil!')
                    return
                # -> Add the score
                else:
                    scores[player] += score

def setup(bot):
    bot.add_cog(Diezmil(bot))
