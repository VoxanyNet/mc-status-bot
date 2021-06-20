from mcstatus import MinecraftServer
import discord
from discord.ext import commands
import time
import asyncio
import datetime

ip = "voxany.net"

print(f"Listening on {ip}")

mc_server = MinecraftServer(ip, 25565)

bot = commands.Bot(command_prefix = "!")

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Loading Stats..."))
    print("Started")

@bot.command()
async def status(ctx):
    mc_status = mc_server.status()
    player_list = ""
    
    current_time = time.time()
    
    print(bot.players_stats)
    
    if bot.players_stats != {}:
        for player in bot.players_stats:
            time_played = datetime.timedelta(seconds = int(current_time - bot.players_stats[player]))
            player_list += f"{player}: {time_played}\n"

        status_message = f"**{mc_status.players.online}/{mc_status.players.max}** players online.\n`{player_list}`"
        
        await ctx.send(status_message)
    else:
        status_message = f"**{mc_status.players.online}/{mc_status.players.max}** players online.\n"
        await ctx.send(status_message)

async def status_update():
    bot.players_stats = {}
    
    players_online = []
    
    pop_buffer = []
    
    await bot.wait_until_ready()
    while True:
        try:
            # Retrieve new stats
            mc_status = mc_server.status()
            
            try:
                # Creates a list of players online
                for player in mc_status.players.sample:
                    players_online.append(player.name)
            except:
                pass
            
            # Checks if each player online is in the player stats dictionary
            for player in players_online:
                if player not in bot.players_stats:
                    bot.players_stats.update({player:time.time()})
                
            # Checks if each player in the stats dictionary is online
            for player in bot.players_stats:
                if player not in players_online:
                    # If they are not online, we remove them from the stats dictionary
                    pop_buffer = []
                    pop_buffer.append(player)
            
            # Commits the buffered pops to the dictionary
            for player in pop_buffer:
                bot.players_stats.pop(player)
            
            players_online = []
            
            pop_buffer = []
            
            
            # Construct status message
            status_message = f"{mc_status.players.online}/{mc_status.players.max} players online."
            
            # Updates status message with the constructed message
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status_message))
        except:
            raise
            status_message = "Loading Stats..."
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status_message))
        await asyncio.sleep(10)

bot.loop.create_task(status_update())    

bot.run("[insert token here]")