import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from db import get_db_connection
from logger import logger

class slashcommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_event", description="Set an event")
    @app_commands.describe(date="YYYY-MM-DD", event_name="Name of Event", message="Details of event",
                           priority="Priority Level", frequency="Event Frequency")
    @app_commands.choices(priority=[
        app_commands.Choice(name="High", value="high"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="Low", value="low")
    ])
    @app_commands.choices(frequency=[
        app_commands.Choice(name="Daily", value="daily"),
        app_commands.Choice(name="Weekly", value="weekly"),
        app_commands.Choice(name="Yearly", value="yearly"),
        app_commands.Choice(name="Once", value="once")
    ])
    async def set_event(self, 
                        interaction: discord.Interaction, 
                        date: str, 
                        event_name: str, 
                        message: str,
                        priority: app_commands.Choice[str] = None, 
                        frequency: app_commands.Choice[str] = None):

        user_id = interaction.user.id
        username = interaction.user.name
        priority_val = priority.value if priority else "high"
        frequency_val = frequency.value if frequency else "once"

        try:
            event_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            await interaction.response.send_message("Invalid date format. Use YYYY-MM-DD.", ephemeral=True)
            logger.info(f"ValueError occur for {username}:{user_id}")
            return

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM user_details WHERE User_id=%s", (user_id,))
        user_exists = cur.fetchone()

        if not user_exists:
            password = username + str(datetime.today().date())
            cur.execute("INSERT INTO user_details (User_name, User_id, User_password) VALUES (%s, %s, %s)",
                        (username, user_id, password))
            cur.execute("INSERT INTO event_details (Date, Event_Name, Message, Priority, Frequency, Username, User_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",(event_date, event_name, message, priority_val, frequency_val, username, user_id))
            conn.commit()
            logger.info(f"{username}:{user_id} user login and {event_name} event successfully added in DB ")

            await interaction.response.send_message(f"{event_name} successfully added for {username} on {event_date}")
            await interaction.followup.send(f"UserName:{username}, Password:{password} is your login credentials", ephemeral=True)
            cur.close()
            conn.close()
            return

        cur.execute("INSERT INTO event_details (Date, Event_Name, Message, Priority, Frequency, Username, User_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",(event_date, event_name, message, priority_val, frequency_val, username, user_id))
        conn.commit()

        if event_date <= datetime.today().date():
            cur.close()
            conn.close()
            await interaction.response.send_message(f"{event_name} successfully added for {username} on {event_date} but The entered date is in Past you will not get any notification.")
            return

        await interaction.response.send_message(f"{event_name} successfully added for {username} on {event_date}")
        cur.close()
        conn.close()