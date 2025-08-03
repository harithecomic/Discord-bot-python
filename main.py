import os
from discord.ext import commands
from dotenv import load_dotenv
import discord
from mysql_utils import init_mysql, get_mysql_connection
from commands import register_commands
from logger import setup_logger

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Setup logger
logger = setup_logger()

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    
    # Initialize MySQL connection and verify it
    success = await init_mysql()
    if not success:
        logger.error("Failed to connect to MySQL. Shutting down bot.")
        await bot.close()
    else:
        logger.info("MySQL connection established successfully.")

# Register commands with the bot
register_commands(bot, logger)


# @bot.command(name='ping')
# async def ping(ctx):
#     await ctx.send('pong')
#     if isinstance(ctx.channel, discord.DMChannel):
#         # Message sent in DM
#         print(f"[DM] Pong sent successfully to user: {ctx.author}")
#     else:
#         # Message sent in a server/guild channel
#         print(f"[Guild] Pong sent in response to {ctx.author} on server '{ctx.guild.name}', channel '{ctx.channel.name}'")

if __name__ == "__main__":
    bot.run(TOKEN)