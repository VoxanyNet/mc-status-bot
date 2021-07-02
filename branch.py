from mcstatus import MinecraftServer
import discord
from discord.ext import commands
import time
import asyncio
import datetime
from mcrcon import MCRcon
import pickle
import atexit

# Generic Functions
def time_convert(delta):
    buffer = ""
    for key,section in enumerate(str(datetime.timedelta(seconds=int(delta))).split(":")):
        if key == 0 and int(section) == 1:
            buffer += f"{int(section)} hour, "
        elif key == 0 and int(section) > 1:
            buffer += f"{int(section)} hours, "
        
        if key == 1 and int(section) == 1:
            buffer += f"{int(section)} minute and "
        elif key == 1 and int(section) > 1:
            buffer += f"{int(section)} minutes and "
        
        if key == 2 and int(section) == 1:
            buffer += f"{int(section)} second"
        elif key == 2 and int(section) > 1:
            buffer += f"{int(section)} seconds"
    return buffer

def get_players_online(instance):
    online = []
    try:
        for player in instance.mc_status.players.sample:
            online.append(player.name)
            #print(f"Added {player.name} to online list!")
        return online
    except:
        #print("No one is online!")
        return online
   
def save_instances():
    # Clears socket objects as they cannot be pickled
    for instance in bot.instances.values():
        print(instance)
        instance.mcr = None
        instance.mc_server = None
    instances_save = open("instances.data","wb")
    pickle.dump(bot.instances,instances_save)
    instances_save.close()
    print("Saved instances!")

async def shutdown_instance(instance,guild_id):
    # Sets instances status to offline
    instance.online = False
    
    # Removes the objects blah blah blah
    instance.mc_server = None
    
    instance.mcr = None
    
    instance_guild = bot.get_guild(guild_id)
    
    await instance_guild.get_member(bot.user.id).edit(nick="Server Offline")
            
    print(f"Set {guild_id}'s server to offline")

def get_instance(guild_id):
    try:
        instance = bot.instances[guild_id]

    except:
        raise Exception("Unable to find server instance")
    
    if instance.online == True:
        return instance
    
    else:
        raise Exception("Server is offline")
        
class Instance:
    def __init__(self,ip,port,rcon_pass):
        self.ip = ip
        self.port = int(port)
        self.rcon_pass = rcon_pass
        
        self.players_stats = {}
        self.players_online = []
        
        self.online = True
        
    def boot(self,guild_id):
        print(f"Booting {guild_id}")
        if self.rcon_pass != None:
            try:
                self.mcr = MCRcon(self.ip, self.rcon_pass)
                self.mcr.connect()

            except:
                # Disables RCON
                self.rcon_pass = None
        
        try:
            # Attempts to make connection to server
            self.mc_server = MinecraftServer(self.ip, self.port)
            self.online = True
        except:
            # Commits suduko
            shutdown_instance(self,guild_id)
        
class Stats:
    def __init__(self):
        self.online = True
        self.last_seen = time.time()
        self.join_time = time.time()

bot = commands.Bot(command_prefix = "!")

# Reloads instances in memory
try:
    instances_load = open("instances.data","rb")
    bot.instances = pickle.load(instances_load)
    instances_load.close()
    print(bot.instances)

except:
    print("Could not find instances file!")
    
    bot.instances = {}

# Boots all instances
for guild_id, instance in bot.instances.items():
    instance.boot(guild_id)

bot.help_messages = {
    "status": "**!status [player]** - Lists all online players with their session playtimes",
    "lastseen": "**!lastseen [player]** - Displays time elapsed since player's last log-off",
    "whitelist": "**!whitelist [player]** - Adds specified player to the whitelist"
    }

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Loading Stats..."))
    print("Started")

@bot.command()
async def contextual(ctx):
    await ctx.send(bot.user.id)

# Creates a new server instance    
@bot.command()
async def connect(ctx,ip,port,password = None):

    # Creates server instance
    new_instance = Instance(ip,port,password)
    
    # Adds instance to dictionary of instances
    bot.instances.update({ctx.message.guild.id:new_instance})
    
    # Connects to the instance
    bot.instances[ctx.message.guild.id].boot(ctx.message.guild.id)
    
    print(bot.instances)

# Reconnects existing server instance
@bot.command()
async def reconnect(ctx):
    instance = bot.instances[ctx.message.guild.id]
    
    instance.boot(ctx.message.guild.id)
    
@bot.command()
async def mchelp(ctx,command = None):
    if command == None:
        buffer = ""
        for help_message in bot.help_messages.values():
            buffer += f"{help_message} \n\n"
        await ctx.send(buffer)
    else:
        await ctx.send(bot.help_messages[command])
   

@bot.command()
async def kick(ctx,user):
    # Loads instance
    try:
        instance = get_instance(ctx.message.guild.id)
    except:
        await ctx.send("Could not connect to your server.")
        return
    
    if instance.rcon_pass == None:
        await ctx.send("You must supply an RCON password for this command to work!\nType !rcon for more info.")
        return
        
    roles = []
    for role in ctx.author.roles:
        roles.append(role.name)
    
    if "Kicker" in roles:
        resp = instance.mcr.command(f"/kick {user}")
        await ctx.send(f"``{resp}``")
        
    else:
        await ctx.send("Insufficient permissions")
        
@bot.command()
async def whitelist(ctx,user):     
    try:
        instance = get_instance(ctx.message.guild.id)
    except:
        await ctx.send("Could not connect to your server.")
        return
    
    if instance.rcon_pass == None:
            await ctx.send("You must supply an RCON password for this command to work!\nType !rcon for more info.")
            return
            
    roles = []
    for role in ctx.author.roles:
        roles.append(role.name)
    
    if "Whitelister" in roles:
        resp = instance.mcr.command(f"/whitelist add {user}")
        await ctx.send(f"``{resp}``")
        
    else:
        await ctx.send("Insufficient permissions")

# Returns a list of players with their time played in the current session
@bot.command()
async def status(ctx):
    try:
        instance = get_instance(ctx.message.guild.id)
    except:
        await ctx.send("Could not connect to your server.")
        return
        
    instance.mc_status = instance.mc_server.status()
    player_list = ""
    
    current_time = time.time()
    
    if instance.players_online != []:
        for player in instance.players_stats:
            if instance.players_stats[player].online == True:
                time_played = datetime.timedelta(seconds = int(current_time - instance.players_stats[player].join_time))
                player_list += f"{player}: {time_played}\n"
            else:
                pass

        status_message = f"**{instance.mc_status.players.online}/{instance.mc_status.players.max}** players online.\n`{player_list}`"
        
        await ctx.send(status_message)
    else:
        status_message = f"**{instance.mc_status.players.online}/{instance.mc_status.players.max}** players online.\n"
        await ctx.send(status_message)

@bot.command()
async def lastseen(ctx,user):
    try:
        instance = get_instance(ctx.message.guild.id)
    except:
        await ctx.send("Could not connect to your server.")
        return
    
    # We first check if the player is online
    if user not in instance.players_stats:
        await ctx.send(f"I have not seen **{user}**")
        
    if user in instance.players_online:
        await ctx.send(f"{user} is currently online!")
    else:
        await ctx.send(f"**{user}** was last seen **{time_convert(time.time() - instance.players_stats[user].last_seen)}** ago")

# Main loop of bot
async def status_update():
    
    await bot.wait_until_ready()
    
    while True:
        #print("==================")
        try:
            # We are going to update the list of online players, so we clear our current list
            for guild_id, instance in bot.instances.items():
                # First checks to see if server is offline
                if instance.online == False:
                    # If the server is offline we move onto the next instance
                    print(f"{guild_id}'s instance is offline.")
                    continue
                instance.players_online = []
            #print("Clearing list of online players!")
            
            # Retrieve new stats
            #print("Retrieving new stats!")
                instance.mc_status = instance.mc_server.status()
            
            # Creates a list of players online
            #print("Getting list of players online!")
                instance.players_online = get_players_online(instance)
            
                # Checks if each player online is in the player stats dictionary
                for player in instance.players_online:
                    if player not in instance.players_stats:
                        #print(f"Adding {player} to stats dictionary!")
                        # If player online does exist in stats dictionary,
                        # we add them, along with a corresponding "Stats" object
                        instance.players_stats.update({player:Stats()})

                    if instance.players_stats[player].online == False:
                        #print(f"Updating {player}'s status to online!")
                        instance.players_stats[player].online = True
                        instance.players_stats[player].join_time = time.time()
                        #print(f"{player}'s join time is {bot.players_stats[player].join_time}")
            
            #for player in bot.players_online:
                #bot.players_stats[player].online = True
                
            # Checks if each player in the stats dictionary is online
                for player in instance.players_stats:
                    if player not in instance.players_online and instance.players_stats[player].online == True:
                            # If they are not online, (and we have not already updated thier status),
                            # we update their stats object to be false
                            #print(f"Updating {player}'s status to offline!")
                            instance.players_stats[player].online = False
                            instance.players_stats[player].last_seen = time.time()
            
                # Construct status message
                #print("Constructing status message!")
                status_message = f"{instance.mc_status.players.online}/{instance.mc_status.players.max} players online."
                
                instance_guild = bot.get_guild(guild_id)
                
                await instance_guild.get_member(bot.user.id).edit(nick=status_message)
        except:
            print(f"Setting {guild_id}'s status to offline.")
            
            await shutdown_instance(instance,guild_id)
            
        await asyncio.sleep(10)
        
bot.loop.create_task(status_update())

atexit.register(save_instances)

bot.run("i promise discord i will not forget to remove my token before pushing to gitgub")