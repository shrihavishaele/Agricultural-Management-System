from flask import Flask, request, render_template, redirect, jsonify, session, url_for
from flask_cors import CORS
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app, supports_credentials=True)
app.secret_key = 'your_secret_key_here'  # Change this to a secure random string

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname="project",
    user="postgres",
    password="1234",
    host="localhost",
    port="5432"
)
conn.autocommit = False  # Explicitly control transactions

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data['email']
    password = data['password']
    
    try:
        cursor = conn.cursor()
        # Check if user exists
        cursor.execute("SELECT farmer_id, farmer_name, password FROM farmer WHERE email_id = %s;", (email,))
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'Email not registered. Please create an account.'
            }), 401
            
        if not user[2]:  # Password is NULL or empty
            return jsonify({
                'success': False,
                'message': 'Password not set. Please reset your password.'
            }), 401
            
        # Compare passwords - ideally we'd use check_password_hash, but if passwords are stored as plaintext initially
        if password == user[2]:  # Direct comparison for non-hashed passwords
            # Create session
            session['user_id'] = user[0]
            session['username'] = user[1]
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user[0],
                    'username': user[1]
                },
                'redirect': '/role'  # Add redirect to role page
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Incorrect password. Please try again.'
            }), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data['name']
    email = data['email']
    password = data['password']
    address = data.get('address', '')  # Optional
    contact = data['contact']  # Required
    
    try:
        cursor = conn.cursor()
        # Check if email already exists
        cursor.execute("SELECT farmer_id FROM farmer WHERE email_id = %s;", (email,))
        if cursor.fetchone():
            cursor.close()
            return jsonify({
                'success': False,
                'message': 'Email already registered. Please login instead.'
            }), 409
        
        # Insert new user with password
        cursor.execute(
            "INSERT INTO farmer (farmer_name, email_id, password, address, contact_no) VALUES (%s, %s, %s, %s, %s) RETURNING farmer_id;",
            (name, email, password, address, contact)
        )
        
        user_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        
        # Create session
        session['user_id'] = user_id
        session['username'] = name
        
        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'user': {
                'id': user_id,
                'username': name
            },
            'redirect': '/role'  # Add redirect to role page
        })
    except Exception as e:
        conn.rollback()
        if 'cursor' in locals():
            cursor.close()
        return jsonify({'error': str(e)}), 500

@app.route('/profile', methods=['GET'])
def get_profile():
    if 'user_id' not in session:
        return jsonify({
            'success': False,
            'message': 'Not logged in'
        }), 401
    
    user_id = session['user_id']
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT farmer_id, farmer_name, email_id, address, contact_no FROM farmer WHERE farmer_id = %s;",
            (user_id,)
        )
        
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            'user': {
                'id': user[0],
                'name': user[1],
                'email': user[2],
                'address': user[3],
                'contact': user[4]
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/check-session', methods=['GET'])
def check_session():
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': session['user_id'],
                'username': session['username']
            }
        })
    else:
        return jsonify({'authenticated': False})

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/role')
def role():
    # If user is not logged in, redirect to home
    if 'user_id' not in session:
        return redirect('/')
    
    # Get username from session (defaulting to 'Guest' if not found)
    username = session.get('username', 'Guest')
    return render_template('role.html', username=username)

@app.route('/farmer')
def farmer_dashboard():
    if 'user_id' not in session:
        return redirect('/')
    
    username = session.get('username', 'Guest')
    return render_template('farmer_dashboard.html', username=username)

@app.route('/buyer')
def buyer_dashboard():
    if 'user_id' not in session:
        return redirect('/')
    
    username = session.get('username', 'Guest')
    return render_template('buyer_dashboard.html', username=username)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    
    username = session.get('username', 'Guest')
    return render_template('dashboard.html', username=username)
# Make sure the directory structure exist