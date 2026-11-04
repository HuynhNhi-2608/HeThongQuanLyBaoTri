from flask import Flask, render_template
from db_config import get_db_connection

app = Flask(__name__)
@app.route('/test-db')
def test_db():
    try:
        conn = get_db_connection()
        if conn:
            # Lấy thông tin phiên bản SQL Server để xác nhận
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            row = cursor.fetchone()
            conn.close()
            return f"<h3>Kết nối SQL Server THÀNH CÔNG!</h3><p>Thông tin server: {row[0]}</p>"
        else:
            return "<h3>KẾT NỐI THẤT BẠI: Không thể tạo connection.</h3>"
    except Exception as e:
        return f"<h3>KẾT NỐI THẤT BẠI:</h3><p>Chi tiết lỗi: {e}</p>"

@app.route('/')
def index():
    # Code test thử kết nối DB (Bỏ comment để test khi đã có Database)
    # conn = get_db_connection()
    # if conn:
    #     print("Đã kết nối SQL Server thành công!")
    #     conn.close()
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)