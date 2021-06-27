from mcstatus import MinecraftServer
import discord
from discord.ext import commands
import time
import asyncio
import datetime
from mcrcon import MCRcon
import pickle
import atexit

class Stats:
    def __init__(self):
        self.online = True
        self.last_seen = time.time()
        self.join_time = time.time()

class Instance:
    def __init__(self,ip,port,rcon_pass):
        self.ip = ip
        self.port = int(port)
        self.rcon_pass = rcon_pass
        self.players_online = []
        
        self.players_stats = {}
            
        self.boot()
        
    def boot(self):
        self.mc_server = MinecraftServer(self.ip, self.port)
        
        if self.rcon_pass != None:
            print("RCON password was supplied!")
            self.mcr = MCRcon(self.ip,self.rcon_pass)
            self.mcr.connect()
        


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

# Connects to all rcon servers    
for instance in bot.instances.values():
    instance.boot()

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
async def connect(ctx,ip,port,password = None):
    
    new_instance = Instance(ip,port,password)
    
    bot.instances.update({ctx.message.guild.id:new_instance})
    
    print(bot.instances)
    
    await ctx.send(f"Succesfully added {ip} to list!")

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
        instance = bot.instances[ctx.message.guild.id]
    except:
        await ctx.send("Could not find your server.")
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
        instance = bot.instances[ctx.message.guild.id]
    except:
        await ctx.send("Could not find your server.")
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
        instance = bot.instances[ctx.message.guild.id]
    except:
        await ctx.send("Could not find your server.")
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
        instance = bot.instances[ctx.message.guild.id]
    except:
        await ctx.send("Could not find your server.")
        return
        
    # We first check if the player is online
    if user not in instance.players_stats:
        await ctx.send(f"I have not seen **{user}**")
        
    if user in instance.players_online:
        await ctx.send(f"{user} is currently online!")
    else:
        await ctx.send(f"**{user}** was last seen **{time_convert(time.time() - instance.players_stats[user].last_seen)}** ago")

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
    
# Main loop of bot
async def status_update():
    
    await bot.wait_until_ready()
    
    while True:
        
        #print("==================")
        
        # We are going to update the list of online players, so we clear our current list
        for instance in bot.instances.values():
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
        #status_message = f"{bot.mc_status.players.online}/{bot.mc_status.players.max} players online."
        
        # Updates status message with the constructed message
        #print("Updating status message!")
        #await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status_message))
        
        #print("Could not load stats!")
        status_message = "Loading Stats..."
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status_message))
        
        await asyncio.sleep(10)
        
bot.loop.create_task(status_update())

atexit.register(save_instances)

bot.run("ODUxNDQyNjAwOTc1OTI1Mjc5.YL4Vtw.3f36VnQClRRDE3tc1fTclx0Pzt0")