from db_config import get_db_connection

try:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DB_NAME()")
    database = cursor.fetchone()[0]

    print("Ket noi thanh cong!")
    print("Database:", database)

    conn.close()

except Exception as e:
    print("Ket noi that bai!")
    print("Chi tiet loi:", e)
