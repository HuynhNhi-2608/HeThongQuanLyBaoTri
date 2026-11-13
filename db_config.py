
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    driver = os.getenv(
        "DB_DRIVER",
        "ODBC Driver 17 for SQL Server"
    )
    auth = os.getenv("DB_AUTH", "windows")

    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "TrustServerCertificate=yes;"
    )

    if auth == "windows":
        conn_str += "Trusted_Connection=yes;"
    else:
        conn_str += (
            f"UID={os.getenv('DB_USER')};"
            f"PWD={os.getenv('DB_PASS')};"
        )

    return pyodbc.connect(conn_str, timeout=5)
