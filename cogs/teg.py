import os
import re
import sys
import json
import random
import discord
import subprocess
from discord.ext import commands

separator = ","

def check(author, channel_id):
    def inner_check(message):
        return message.author == author and message.channel.id == channel_id
    return inner_check

async def get_member_object(self,ctx,text):
    try:
        member_id = re.findall(r'<@!(\d+)>',text)[0]
    except:
        return False
    member = ctx.guild.get_member(int(member_id))
    return member

async def print_map(self,ctx,countries_file,maps_folder,country):
    await ctx.send('Imprimiendo mapa...')
    os.system(f'./games/teg/map_editing.py {countries_file} {maps_folder} {country}')
    for temp_map in await get_maps(maps_folder):
        temp_map = discord.File(temp_map)
        await ctx.send(file=temp_map)

async def get_units(text):
    additions = []
    for line in text.split('\n'):
        try:
            regex = re.findall(fr"(\d+){separator}(\w+)", line.replace(' ',''))
            units    = regex[0][0]
            province = regex[0][1]
            additions.append((units,province))
        except:
            return False
    return additions

async def attack_defend(text):
    try:
        regex = re.findall(fr"(\w+){separator}(\w+)",text.replace(' ',''))[0]
        attacker = regex[0]
        defender = regex[1]
        return (attacker, defender)
    except:
        return False

def update_countries_file(countries, countries_file):
    with open(countries_file, 'w') as w:
        w.write(json.dumps(countries))#,indent=4,sort_keys=True))

async def get_maps(maps_folder):
    os.system(maps_folder+f'divide_map {maps_folder}')
    files = sorted([maps_folder+file for file in os.listdir(maps_folder) if file.startswith('crop')])
    return files

async def y_or_n(self, ctx, channel_id, player, action):
    """
    Asks the player for a y/n answer, then it return True for positive and False for negative,
    also keeps asking if the answer ain't valid
    """
    message = 0
    while True:
        await ctx.send(f'{player}, deseas {action}? (si/no)')
        message = await self.bot.wait_for('message',check=check(await get_member_object(self,ctx,player),channel_id))
        message = message.content
        if message == 'no' or message == 'n':
            await ctx.send('ok!')
            return False
        if message == 'si' or message == 'y':
            return True

async def get_players(self, ctx, number_of_players, channel_id):
    number_of_players = int(float(number_of_players))
    players = dict()
    available_colors = ['red','black','blue','yellow','green']

    await ctx.send(f'''
            Envía un mensaje, respetando el siguiente formato:
            > `@jugador1,color1`
            > `@jugador2,color2`
            > `@jugador3,color3`
            
            ``` 
            Los colores disponibles son: {available_colors}
            ''')
    msj = await self.bot.wait_for('message',check=check(ctx.author, channel_id))
    players_list = msj.content.split('\n')
    # Split the message and get the first character before the commas and the one after  and iterate through them
    for player, color in [(pl.split(',')[0].replace(' ',''),pl.split(',')[1].replace(' ', '')) for pl in players_list]:
        counter = 0
        if player in players:
            continue
        # Check if the tagged player is tagged correctly
        member = await get_member_object(self,ctx,player)
        while not member:
            await ctx.send(f'El tag de {player} no es válido, enviar de nuevo el tag solo:')
            #<TODO> PROBAR SI ESTO ANDA
            member = await get_member('message')
        # Check if the color is available
        while color not in available_colors:
            await ctx.send(f'El color de {player} no es válido, envía un mensaje con solo un color válido')
            #<TODO> ACTUALIZAR EL WAIT_FOR PARA QUE RESTRINJA
            color = self.bot.wait_for('message',check=check(await get_member_object(self,ctx,player),channel_id)) #color = await self.bot.wait_for('message')
            color = color.content
        # Add the player to the dictionary
        players[player] = {'color':color, 'provinces':[]}
        # Drop the color
        available_colors.remove(color)
    return players

async def assign_countries(self, ctx, players_list, countries, country,countries_file):
    """
    Makes a list of all the provinces, shuffles it and then assings them to the players by cycling through the players
    """
    province_list = [province for province in countries[country]]
    random.shuffle(province_list)
    while province_list != []:
        for player in players_list:
            if province_list == []:
                return players_list
            players_list[player]['provinces'].append(province_list[0])
            province_list.pop(0)

async def send_objectives(self, ctx, players, country, objectives_file):
    with open(objectives_file) as f:
        objectives_list = f.readlines()
    for player in players:
        objective = random.choice(objectives_list)
        players[player]['objective'] = objective
        objectives_list.remove(objective)
        member = await get_member_object(self,ctx,player)
        await member.send(f'Tu objetivo es: {players[player]["objective"]}')
    return players

async def start_values(self, ctx, players, country, countries_file):
    with open(countries_file) as f:
        countries = json.loads(f.read())
    for player in players:
        for province in players[player]['provinces']:
            countries[country][province]['units'] = "1"
            countries[country][province]['owner'] = players[player]['color']
    update_countries_file(countries, countries_file)
    return countries

async def add_units(self, ctx, country, player, players, countries, countries_file,maps_folder,max_amount,channel_id):
    amount = max_amount
    while amount > 0:
        await ctx.send(f'''Turno de {player}:
                puede sumar un total de {amount} unidades, respetando el formato:
                > `número,tag del país`
                > `número,tag del país`
                > etc''')
        msj = await self.bot.wait_for('message',check=check(await get_member_object(self,ctx,player),channel_id))
        add = await get_units(msj.content)

        if add:
            # Check if the total amount to add is equal or inferior to the available amount
            total_amount = 0
            for (units, province) in add:
                total_amount += int(units)
                # Check if the province is owned by the player
                if province not in players[player]['provinces']:
                    await ctx.send(f'No posees la provincia {province}')
                    total_amount = 9999999999
                    break

            # Check if the total amount to add corresponds with the max amount the player can add
            if total_amount <= amount:
                for (units, province) in add:
                    current_amount = int(countries[country][province]['units'])
                    current_amount += int(units)
                    countries[country][province]['units'] = str(current_amount)
                    amount -= total_amount
            else:
                await ctx.send(f"No puedes añadir esa cantidad de unidades, o no posees una de las provincias, vuelve a intentarlo!")
    # Update countries file and return the countries variable
    update_countries_file(countries, countries_file)
    await print_map(self,ctx,countries_file,maps_folder,country)
    return countries

async def province_exists(self, ctx, country, countries, province):
    if province in countries[country].keys():
        return True
    else:
        return False

async def is_attack_possible(self, ctx, player, players, country, countries,attack_province, defense_province):
    """
    First check if the player owns the attacker province and not the owner province.
      Also if the attack province has more than 1 unit
    """
    if not await province_exists(self,ctx,country,countries,attack_province):
        return False
    elif not await province_exists(self,ctx,country,countries,defense_province):
        return False
    elif not (attack_province in players[player]['provinces']):
        return False
    elif not (defense_province in countries[country][attack_province]['limits']):
        return False
    elif not (int(countries[country][attack_province]['units']) > 1):
        return False
    else:
        return True


async def dice_rolls(units):
    """
    Roll a dice for each units, with a max of 3 rolls, then returns all the results as a reverse ordered list
    """
    rolls = []
    for i in range(units):
        rolls.append(random.randint(1,6))
        if i == 2:
            break
    return sorted(rolls, reverse = True)

async def get_wins(attack_rolls, defend_rolls):
    results = []
    if len(attack_rolls) < len(defend_rolls):
        for i in range(len(attack_rolls)):
            results.append(attack_rolls[i]-defend_rolls[i])
        return results
    else:
        for i in range(len(defend_rolls)):
            results.append(attack_rolls[i]-defend_rolls[i])
        return results

async def count_attacks(self, ctx, player, players, country, countries, attacker, defender, attack_units,defend_units,results, countries_file,maps_folder):
    # Iterate through all the results
    for result in results:
        if result > 0:
            # If the result is possitive discount a defensive unit
            defend_units -= 1
            if defend_units == 0:
                # If the defensive units reach zero:
                #  - Discount an offensive unit that "moves" to the defensive province
                #  - Make the defensive the color of the attacker and give it a value of 1 unit
                #  - Search for the player that lost their province and remove it from their list, later add it to the attacker's list
                # Unit that moves to the other province
                attack_units -= 1
                defend_units = 1
                # Change ownership and (amount of units) -> more general change at the end of the script
                countries[country][defender]['owner'] = countries[country][attacker]['owner']
                
                #countries[country][defender]['units'] = str(1)
                # Change amount of units of the attacker too
                # 
                # Now it's changed below!
                # countries[country][attacker]['units'] = str(attack_units)

                # Look for the loser and take out their province, then do the oposite for the winner
                for p in players:
                    if defender in players[p]['provinces']:
                        await ctx.send(f'Expropiando a {p} de {defender}')
                        players[p]['provinces'].remove(defender)
                players[player]['provinces'].append(defender)
                break
        else:
            attack_units -= 1
        
    countries[country][attacker]['units'] = str(attack_units)
    countries[country][defender]['units'] = str(defend_units)
    
    update_countries_file(countries,countries_file)
        
    await print_map(self,ctx,countries_file,maps_folder,country)
    return players, countries

async def can_attack(self,ctx,player,players,country,countries):
    for province in players[player]['provinces']:
        if int(countries[country][province]['units']) > 1 and 'limit not owned' in ['limit not owned' for i in countries[country][province]['limits'] if i not in players[player]['provinces']]:
                return True
    return False

async def attack(self, ctx, player,players,country,countries,channel_id,countries_file,maps_folder):
    if await y_or_n(self, ctx, channel_id, player, 'atacar'):
        while True:
            if not await can_attack(self,ctx,player,players,country,countries):
                await ctx.send(f'{player} no puede atacar, siguiente.')
                return players,countries

            await ctx.send(f'''**Ataque de {player}**
                    Ingresa con quién quieres atacar y contra quién, separados por {separator}
                    > atacante{separator}atacado''')
            message = await self.bot.wait_for('message',check=check(await get_member_object(self,ctx,player),channel_id))
            
            if message.content == 'cancel':
                await ctx.send('Ataque cancelado!')
                return (players, countries)
            try:
                (attacker, defender) = await attack_defend(message.content)
            except:
                await ctx.send('Mensaje no válido!')
                continue

            if not await is_attack_possible(self,ctx,player,players,country,countries,attacker,defender):
                await ctx.send('Ataque no válido')
                continue
            
            attack_units = int(countries[country][attacker]['units'])
            defend_units = int(countries[country][defender]['units'])
            
            attack_rolls = await dice_rolls(attack_units-1)
            defend_rolls = await dice_rolls(defend_units)
            await ctx.send(f'Dados de ataque: {attack_rolls}')
            await ctx.send(f'Dados de defensa: {defend_rolls}')
            results = await get_wins(attack_rolls, defend_rolls)

            (players, countries) = await count_attacks(self, ctx, player, players, country, countries, attacker, defender, attack_units,defend_units,results, countries_file,maps_folder) 

            if not await y_or_n(self,ctx,channel_id,player,'seguir atacando'):
                return players,countries 
    else:
        return players,countries

async def init_can_move(self,ctx, player, players, country, countries):
    for province in players[player]['provinces']:
        if int(countries[country][province]['units']) > 1 and \
           'limit owned' in ['limit owned' for i in countries[country][province]['limits'] if i in players[player]['provinces']]:
           return True
    return False

async def units_from_to(text):
    try:
        regex = re.findall(fr"(\d+){separator}(\w+){separator}(\w+)",text.replace(' ','').lower())[0]
        units       = int(regex[0])
        origin      = regex[1]
        destination = regex[2]
        return (units, origin, destination)
    except:
        return False

async def can_move(self,ctx,player,players,country,countries,origin, destination, units):
    if origin in players[player]['provinces'] and destination in players[player]['provinces'] and units >= 1 and int(countries[country][origin]['units']) > units:
        return True
    else:
        return False

async def regroup(self, ctx, player, players, country, countries, channel_id,countries_file,maps_folder):
    if await y_or_n(self, ctx, channel_id, player, 'reagrupar unidades'):
        while True:
            if not await init_can_move(self, ctx, player, players, country, countries):
                await ctx.send(f'{player} no puede reagruparse, siguiente.')
                return players,countries
            await ctx.send(f'''**Reagrupación de {player}**
                    Ingresa cuantas unidades deseas desplazar, desde donce y hacia donde, separados con: `{separator}`
                    envía 'cancel' para cancelar la acción.
                    > `num unidades{separator}desde{separator}hacia`''')
            message = await self.bot.wait_for('message',check=check(await get_member_object(self,ctx,player),channel_id))
            if message.content == 'cancel':
                await ctx.send('Reagrupación cancelada!')
                return (players, countries)
            
            try:
                (units, origin, destination) = await units_from_to(message.content)
            except:
                await ctx.send('Mensaje no válido!')
                continue
            if not await can_move(self,ctx,player,players,country,countries,origin, destination, units):
                await ctx.send('Movimiento no válido!')
                continue

            countries[country][origin]['units'] = str(int(countries[country][origin]['units']) - units)
            countries[country][destination]['units'] = str(int(countries[country][destination]['units']) + units)
            
            update_countries_file(countries,countries_file)
            await print_map(self,ctx,countries_file,maps_folder,country)
            
            if not await y_or_n(self, ctx, channel_id, player, 'mover más unidades'):
                return players, countries

    else:
        return players, countries


class Teg(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def teg(self, ctx, country='argentina',first_add_units = 8, add_percentaje = 0.5, win_porcentaje=0.6):

        # Config the script with:
        # - The path to the file where all the countries are
        # - The path to the file that holds the country's objectives:
        #       The objectives file must be a plain text file where each line corresponds to an objective
        # - The folder that holds all the maps
        # - The amonut of units that will be added in the add phase
        # TODO the path should be guild-dependandt
        countries_file = './games/teg/countries.json'
        objectives_file=f'./games/teg/objectives/objectives_{country}.txt'
        maps_folder = f'./games/teg/maps/'
        number_of_players=0
        channel_id = ctx.channel.id
        with open(countries_file) as f:
            countries = json.loads(f.read())
       
        #----> Start of the game
        #_______________________

        # Get the players list and make a dictionary with it,
        #   the one commented can serve as an example of how the end
        #   dictionary would look like.
        
        players = await get_players(self,ctx,number_of_players,channel_id)

        #--> test dictionary
#        koto  = "<@!user's id>"
#        roter = "<@!user2's id>"
#        players = {
#                roter:{"color":'red','provinces':[]},
#                koto:{"color":'blue','provinces':[]}
#                }

        # Distribute the countries between all players
        # - updates the 'provinces' field for each player with their owned provinces
        # - defines a countries dictionary that will hold the map data
        players   = await assign_countries(self,ctx,players,countries,country,countries_file)
        countries = await start_values(self, ctx, players,country, countries_file)

        # Give Objectives
        # - self explanatory
        players   = await send_objectives(self, ctx, players, country, objectives_file)
        
        #
        #----> Start phase
        #_______________________

        # Show the initial map to visualize wich countries each player owns, then:
        # 1. Iterate through each player and ask where should their units be added
        # 2. Print the new map in each iteration
        await ctx.send(f'Comenzando el juego! Objetivo general: _Conquistar el {win_porcentaje*100}\% del mapa_')        
        await print_map(self,ctx,countries_file,maps_folder,country)        
        for player in players:
            countries = await add_units(self, ctx, country, player, players, countries, countries_file, maps_folder,int(first_add_units/2), channel_id)
            await print_map(self,ctx,countries_file,maps_folder,country)
        
        #
        #----> Normal Phase
        #_______________________
        while True:
            #
            #----> Attack Phase
            #_______________________
            await ctx.send('> __**Fase de hostilidades**__')
            for player in players:
                await ctx.send(f'\n> **Turno de {player}**\n')
                await ctx.send(f'\n> **Etapa de ataque de {player}**\n')
                players, countries = await attack(self, ctx, player, players, country,countries, channel_id, countries_file,maps_folder)
                if len(players[player]['provinces']) >= win_porcentaje*len(countries[country].keys()):
                    await ctx.send(f'{player} a ganado tras conquistar {win_porcentaje*100}\% del mapa, muy bien')
                    return
                await ctx.send(f'\n> **Etapa de reagrupación de {player}**\n')
                players, countries = await regroup(self, ctx, player, players, country,countries, channel_id, countries_file,maps_folder)

            #
            #----> Add Phase
            #_______________________
            await ctx.send('> __**Fase de adición**__')
            for player in players:
                await ctx.send(f'\n> **Fase de adición de {player}**\n')
                units_to_add = int(len(players[player]['provinces'])*add_percentaje)
                countries = await add_units(self, ctx, country, player, players, countries, countries_file, maps_folder, units_to_add, channel_id)
            
        #
        #----> End game message
        #_______________________
        await ctx.send('Fin del juego, gay')

def setup(bot):
    bot.add_cog(Teg(bot))
