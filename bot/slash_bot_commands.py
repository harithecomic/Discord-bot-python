import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from db import get_db_connection
from logger import logger

class Paginator(discord.ui.View):
    def __init__(self, user: discord.User, data, old_records, per_page=10):
        super().__init__(timeout=60)
        self.user = user
        self.data = data
        self.per_page = per_page

        # total pages
        self.total_pages = (len(self.data) - 1) // self.per_page + 1

        # ✅ Calculate starting page dynamically
        # Example: if 14 old records with per_page=10 → start_page = 14 // 10 = 1
        self.start_page = old_records // self.per_page
        self.page = self.start_page

        # ✅ Hide buttons if there's only 1 page (<= 10 events)
        if self.total_pages <= 1:
            for item in self.children:
                item.disabled = True
            self.clear_items()

    def format_page(self):
        start = self.page * self.per_page
        end = start + self.per_page
        page_data = self.data[start:end]

        if not page_data:
            return "No events found."

        # Table header
        header = f"{'Event ID':<12} | {'Date':<12} | {'Event Name':<20} | {'Message':<30} | {'Priority':<8} | {'Frequency':<10}"
        separator = "-" * len(header)

        # Table rows
        rows = [
            f"{str(row[0]):<12} | {str(row[1]):<12} | {str(row[2]):<20} | {str(row[3]):<30} | {str(row[4]):<8} | {str(row[5]):<10}"
            for row in page_data
        ]

        table = "\n".join([header, separator] + rows)
        return f"**Your Events (Page {self.page+1}/{self.total_pages})**\n```\n{table}\n```"

    async def update_message(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=self.format_page(), view=self)

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("This is not your paginator!", ephemeral=True)

        if self.page > 0:
            self.page -= 1
            await self.update_message(interaction)
        else:
            await interaction.response.send_message("You are already on the first page.", ephemeral=True)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("This is not your paginator!", ephemeral=True)

        if (self.page + 1) * self.per_page < len(self.data):
            self.page += 1
            await self.update_message(interaction)
        else:
            await interaction.response.send_message("There is no next page.", ephemeral=True)


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


    @app_commands.command(name="show_events", description="Show your saved events")
    async def show_events(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        today_date=str(datetime.today().date()) #EX:2025-08-18

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""SELECT Event_ID, Date, Event_Name, Message, Priority, Frequency FROM event_details WHERE User_id=%s and date<%s""", (user_id,today_date))
        Past_rows = cur.fetchall()
        cur.close()
        conn.close()
        start_page = (len(Past_rows) - 1) // 10 + 1

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""SELECT Event_ID, Date, Event_Name, Message, Priority, Frequency FROM event_details WHERE User_id=%s ORDER BY Date ASC""", (user_id,))
        rows = cur.fetchall()

        cur.close()
        conn.close()

        if not rows:
            await interaction.response.send_message("You have no saved events.")
            return

        view = Paginator(interaction.user, rows, start_page, per_page=10)
        await interaction.response.send_message(content=view.format_page(), view=view)

    @app_commands.command(name="delete_event", description="Delete a event")
    @app_commands.describe(event_id="Enter Event ID")
    async def delete_event(self, 
                        interaction: discord.Interaction, 
                        event_id: int, 
                        ):
        user_id = interaction.user.id
        username = interaction.user.name

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""SELECT EVENT_ID FROM event_details WHERE User_id=%s""", (user_id,))
        Available_Event_ID=cur.fetchall()
        cur.close()
        conn.close()
        print(Available_Event_ID)
        if (event_id,) in Available_Event_ID:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""DELETE FROM event_details WHERE Event_ID=%s""", (event_id,))
            conn.commit()
            cur.close()
            conn.close()
            await interaction.response.send_message(f"{event_id} event successfully deleted.")
        else:
            await interaction.response.send_message(f"You don't have any event for {event_id} event ID")