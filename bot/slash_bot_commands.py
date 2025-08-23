import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from db import get_db_connection
from logger import logger
import os

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
            cur.execute("INSERT INTO event_details (Date, Event_Name, Message, Priority, Frequency, Username, User_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (event_date, event_name, message, priority_val, frequency_val, username, user_id))
            conn.commit()
            logger.info(f"{username}:{user_id} user login and {event_name} event successfully added in DB ")
            await interaction.response.send_message(f"{event_name} successfully added for {username} on {event_date}")
            await interaction.followup.send(f"UserName:{username}, Password:{password} is your login credentials", ephemeral=True)
            cur.close()
            conn.close()
            return

        cur.execute("INSERT INTO event_details (Date, Event_Name, Message, Priority, Frequency, Username, User_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (event_date, event_name, message, priority_val, frequency_val, username, user_id))
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
        today_date = str(datetime.today().date())  # EX:2025-08-18

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""SELECT Event_ID, Date, Event_Name, Message, Priority, Frequency FROM event_details WHERE User_id=%s and date<%s""", (user_id, today_date))
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
                           event_id: int):
        user_id = interaction.user.id
        username = interaction.user.name

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""SELECT EVENT_ID FROM event_details WHERE User_id=%s""", (user_id,))
        Available_Event_ID = cur.fetchall()
        cur.close()
        conn.close()

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

    # NEW IMAGE MANAGEMENT COMMANDS

    def create_user_directory(self, username: str) -> str:
        """Create user directory if it doesn't exist and return the path"""
        user_dir = os.path.join(os.getenv("DATA_ROOT"), username)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir, exist_ok=True)
            logger.info(f"Created directory for user: {username}")
        return user_dir

    def get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename"""
        return os.path.splitext(filename)[1].lower()

    def is_valid_image(self, filename: str) -> bool:
        """Check if the file is a valid image format"""
        valid_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']
        return self.get_file_extension(filename) in valid_extensions

    @app_commands.command(name="upload_image", description="Upload and store an image")
    @app_commands.describe(image_name="Name for the image (without extension)", image="Image file to upload")
    async def upload_image(self,
                          interaction: discord.Interaction,
                          image_name: str,
                          image: discord.Attachment):
        username = interaction.user.name

        try:
            # Validate that the uploaded file is an image
            if not self.is_valid_image(image.filename):
                await interaction.response.send_message(
                    "❌ Invalid file type. Please upload a valid image file (PNG, JPG, JPEG, GIF, WEBP, BMP).",
                    ephemeral=True
                )
                return

            # Create user directory
            user_dir = self.create_user_directory(username)

            # Get the original file extension
            original_extension = self.get_file_extension(image.filename)

            # Create the full filename with extension
            full_filename = f"{image_name}{original_extension}"
            file_path = os.path.join(user_dir, full_filename)

            # Check if file already exists
            if os.path.exists(file_path):
                await interaction.response.send_message(
                    f"❌ An image with the name '{image_name}' already exists. Please use a different name or delete the existing image first.",
                    ephemeral=True
                )
                return

            # Check file size (Discord limits: 8MB for regular users, 50MB for Nitro)
            max_size = 50 * 1024 * 1024  # 50MB in bytes
            if image.size > max_size:
                await interaction.response.send_message(
                    f"❌ File too large. Maximum size is 50MB. Your file is {image.size / (1024*1024):.2f}MB.",
                    ephemeral=True
                )
                return

            # Save the image
            await image.save(file_path)

            logger.info(f"Image '{full_filename}' uploaded by {username} to {file_path}")
            await interaction.response.send_message(
                f"✅ Successfully uploaded image '{image_name}' as {full_filename}!"
            )

        except Exception as e:
            logger.error(f"Error uploading image for {username}: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while uploading the image. Please try again.",
                ephemeral=True
            )

    @app_commands.command(name="list_images", description="List all your uploaded images")
    async def list_images(self, interaction: discord.Interaction):
        username = interaction.user.name
        user_dir = os.path.join(os.getenv("DATA_ROOT"), username)

        try:
            # Check if user directory exists
            if not os.path.exists(user_dir):
                await interaction.response.send_message(
                    "📂 You haven't uploaded any images yet. Use `/upload_image` to get started!",
                    ephemeral=True
                )
                return

            # Get all files in the user directory
            files = os.listdir(user_dir)

            # Filter only image files
            image_files = [f for f in files if self.is_valid_image(f)]

            if not image_files:
                await interaction.response.send_message(
                    "📂 No images found in your directory. Use `/upload_image` to upload some images!",
                    ephemeral=True
                )
                return

            # Sort files alphabetically
            image_files.sort()

            # Create formatted list
            if len(image_files) <= 20:  # Show all if 20 or fewer
                file_list = "\n".join([f"• {f}" for f in image_files])
                message = f"📋 **Your Images ({len(image_files)} total):**\n```\n{file_list}\n```"
            else:  # Show first 20 and indicate there are more
                file_list = "\n".join([f"• {f}" for f in image_files[:20]])
                message = f"📋 **Your Images (showing 20 of {len(image_files)}):**\n```\n{file_list}\n```\n*...and {len(image_files) - 20} more*"

            await interaction.response.send_message(message)
            logger.info(f"Listed {len(image_files)} images for user {username}")

        except Exception as e:
            logger.error(f"Error listing images for {username}: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while listing your images. Please try again.",
                ephemeral=True
            )

    @app_commands.command(name="delete_image", description="Delete an uploaded image")
    @app_commands.describe(image_name="Name of the image to delete (with or without extension)")
    async def delete_image(self,
                          interaction: discord.Interaction,
                          image_name: str):
        username = interaction.user.name
        user_dir = os.path.join(os.getenv("DATA_ROOT"), username)

        try:
            # Check if user directory exists
            if not os.path.exists(user_dir):
                await interaction.response.send_message(
                    "❌ You don't have any uploaded images to delete.",
                    ephemeral=True
                )
                return

            # Get all files in the user directory
            files = os.listdir(user_dir)
            image_files = [f for f in files if self.is_valid_image(f)]

            if not image_files:
                await interaction.response.send_message(
                    "❌ No images found in your directory.",
                    ephemeral=True
                )
                return

            # Find the file to delete (with or without extension)
            file_to_delete = None

            # First, try exact match
            if image_name in image_files:
                file_to_delete = image_name
            else:
                # Try to find by name without extension
                for file in image_files:
                    file_name_without_ext = os.path.splitext(file)[0]
                    if file_name_without_ext.lower() == image_name.lower():
                        file_to_delete = file
                        break

            if not file_to_delete:
                # Show available images for reference
                available_images = "\n".join([f"• {f}" for f in sorted(image_files)[:10]])
                message = f"❌ Image '{image_name}' not found.\n\n**Available images:**\n```\n{available_images}"
                if len(image_files) > 10:
                    message += f"\n...and {len(image_files) - 10} more"
                message += "\n```"

                await interaction.response.send_message(message, ephemeral=True)
                return

            # Delete the file
            file_path = os.path.join(user_dir, file_to_delete)
            os.remove(file_path)

            logger.info(f"Image '{file_to_delete}' deleted by {username}")
            await interaction.response.send_message(
                f"✅ Successfully deleted image: **{file_to_delete}**"
            )

        except Exception as e:
            logger.error(f"Error deleting image for {username}: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while deleting the image. Please try again.",
                ephemeral=True
            )