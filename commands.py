import discord
from datetime import datetime
from mysql_utils import insert_event

def register_commands(bot, logger):
    @bot.command(name='ping')
    async def ping(ctx):
        await ctx.send('pong')

        if isinstance(ctx.channel, discord.DMChannel):
            logger.info(f"[DM] Pong sent successfully to user: {ctx.author}")
        else:
            logger.info(f"[Guild] Pong sent in response to {ctx.author} on server '{ctx.guild.name}', channel '{ctx.channel.name}'")

    @bot.command(name='addevent')
    async def addevent(ctx, date: str, event_name: str, priority: int, *, details: str):
        """
        Add an event to the MySQL database.
        Usage: !addevent YYYY-MM-DD EventName priority_number event_details
        Example:
        !addevent 2025-08-10 "Project Deadline" 1 "Complete the final report"
        """

        # Validate date format
        try:
            event_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            await ctx.send("Invalid date format! Please use YYYY-MM-DD.")
            return
        
        # Insert into DB
        success = insert_event(event_date, event_name, priority, details)
        if success:
            await ctx.send(f"Event '{event_name}' added successfully for {event_date} with priority {priority}.")
            logger.info(f"Event added by {ctx.author}: {event_name} on {event_date} with priority {priority}")
        else:
            await ctx.send("Failed to add event to database.")
            logger.error(f"Failed to insert event: {event_name} by {ctx.author}")
