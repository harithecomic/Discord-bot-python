import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

from logger import logger
from db import create_tables
from slash_bot_commands import slashcommands

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Bot logged in as {bot.user}")
    await bot.add_cog(slashcommands(bot))  # Await here
    await bot.tree.sync()
    logger.info("Slash commands synced.")

if __name__ == "__main__":
    logger.info(f"Main run successfully")
    create_tables()
    bot.run(os.getenv("DISCORD_TOKEN"))