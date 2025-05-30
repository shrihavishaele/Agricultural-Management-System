from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2

app = Flask(__name__)
CORS(app)

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname="project",
    user="postgres",
    password="1234",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

@app.route('/user', methods=['POST'])
def get_user_details():
    data = request.get_json()
    email = data['email']

    try:
        # Modified to get username by email instead
        cursor.execute("SELECT farmer_name FROM farmer WHERE email_id = %s;", (email,))
        result = cursor.fetchone()
        if result:
            return jsonify({'username': result})
        else:
            return jsonify({'username': None})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)