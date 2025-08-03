import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DB = os.getenv('MYSQL_DATABASE')

mysql_conn = None

async def init_mysql():
    """
    Initialize and verify MySQL connection.
    Create 'event_details' table if it doesn't exist.
    Returns True if connected successfully, False otherwise.
    """
    global mysql_conn
    try:
        mysql_conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        if mysql_conn.is_connected():
            cursor = mysql_conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_details (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    event_date DATE NOT NULL,
                    event_name VARCHAR(255) NOT NULL,
                    priority INT NOT NULL,
                    event_details TEXT
                )
            """)
            mysql_conn.commit()
            cursor.close()
            return True
        else:
            return False
    except Error as e:
        print(f"MySQL connection error: {e}")
        return False

def get_mysql_connection():
    """
    Returns the active MySQL connection object.
    """
    return mysql_conn

def insert_event(event_date, event_name, priority, details):
    """
    Insert an event into the event_details table.
    Returns True on success, False on failure.
    """
    global mysql_conn
    if mysql_conn is None or not mysql_conn.is_connected():
        return False

    try:
        cursor = mysql_conn.cursor()
        sql = """
            INSERT INTO event_details (event_date, event_name, priority, event_details)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql, (event_date, event_name, priority, details))
        mysql_conn.commit()
        cursor.close()
        return True
    except Error as e:
        print(f"MySQL insert error: {e}")
        return False
