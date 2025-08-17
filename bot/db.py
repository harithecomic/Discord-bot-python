import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
from logger import logger

load_dotenv()

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE")
        )
        return conn
    except Error as e:
        logger.error(f"Error connecting to MySQL: {e}")
        raise

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_details (
        ID INT AUTO_INCREMENT PRIMARY KEY,
        User_name VARCHAR(255),
        User_id BIGINT,
        User_password VARCHAR(255)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS event_details (
        Event_ID INT AUTO_INCREMENT PRIMARY KEY,
        Date DATE,
        Event_Name VARCHAR(255),
        Message TEXT,
        Priority ENUM('high', 'medium', 'low') DEFAULT 'high',
        Frequency ENUM('daily', 'weekly', 'yearly', 'once') DEFAULT 'once',
        Username VARCHAR(255),
        User_id BIGINT
    )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("MySQL tables ready.")
