from flask import Flask, request, render_template, redirect, jsonify, session, url_for
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from db_config import connect_db
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'your_secret_key_here'  # Change this to a secure random string

# Simulated cart storage (in a real app, use a database table)
cart = []

@app.route('/')
def home():
    return render_template('role.html')

@app.route('/select_role/<role>')
def select_role(role):
    if role not in ['farmer', 'buyer']:
        logger.warning(f"Invalid role selected: {role}")
        return redirect('/')
    session['role'] = role
    logger.debug(f"Role set to: {role}")
    return redirect(url_for('login_page'))

@app.route('/login_page')
def login_page():
    if 'role' not in session:
        logger.warning("No role in session, redirecting to role selection")
        return redirect('/')
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.form
    email = data['email']
    password = data['password']
    role = data.get('role')

    if role not in ['farmer', 'buyer']:
        logger.warning(f"Invalid role in login: {role}")
        return render_template('index.html', error='Invalid role selected.')

    try:
        conn = connect_db()
        cursor = conn.cursor()

        if role == 'farmer':
            cursor.execute("SELECT farmer_id, farmer_name, password FROM farmer WHERE email_id = %s;", (email,))
            user = cursor.fetchone()
            if not user:
                return render_template('index.html', error='Email not registered as a farmer.')
            if not user[2]:
                return render_template('index.html', error='Password not set. Contact admin.')
            if password == user[2]:  # Note: Use check_password_hash if passwords are hashed
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['role'] = 'farmer'
                logger.debug(f"Farmer logged in: {user[0]}")
                return redirect(url_for('farmer_dashboard'))
            else:
                return render_template('index.html', error='Incorrect password.')
        else:  # role == 'buyer'
            cursor.execute("SELECT buyer_id, buyer_name, password FROM buyer WHERE email_id = %s;", (email,))
            user = cursor.fetchone()
            if not user:
                return render_template('index.html', error='Email not registered as a buyer.')
            if not user[2]:
                return render_template('index.html', error='Password not set. Contact admin.')
            if password == user[2]:  # Note: Use check_password_hash if passwords are hashed
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['role'] = 'buyer'
                logger.debug(f"Buyer logged in: {user[0]}")
                return redirect(url_for('buyer_dashboard'))
            else:
                return render_template('index.html', error='Incorrect password.')

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return render_template('index.html', error=str(e))
    finally:
        if conn:
            cursor.close()
            conn.close()

@app.route('/register', methods=['POST'])
def register():
    data = request.form
    name = data['name']
    email = data['email']
    password = data['password']
    address = data.get('address', '')
    contact = data['contact']
    role = data.get('role')

    if role not in ['farmer', 'buyer']:
        logger.warning(f"Invalid role in register: {role}")
        return render_template('index.html', error='Invalid role selected.')

    try:
        conn = connect_db()
        cursor = conn.cursor()

        if role == 'farmer':
            cursor.execute("SELECT farmer_id FROM farmer WHERE email_id = %s;", (email,))
            if cursor.fetchone():
                return render_template('index.html', error='Email already registered as a farmer.')
            cursor.execute(
                "INSERT INTO farmer (farmer_name, email_id, password, address, contact_no) VALUES (%s, %s, %s, %s, %s) RETURNING farmer_id;",
                (name, email, password, address, contact)
            )
            user_id = cursor.fetchone()[0]
            session['user_id'] = user_id
            session['username'] = name
            session['role'] = 'farmer'
            logger.debug(f"Farmer registered: {user_id}")
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('farmer_dashboard'))
        else:  # role == 'buyer'
            cursor.execute("SELECT buyer_id FROM buyer WHERE email_id = %s;", (email,))
            if cursor.fetchone():
                return render_template('index.html', error='Email already registered as a buyer.')
            cursor.execute(
                "INSERT INTO buyer (buyer_name, email_id, password, contact_no, address) VALUES (%s, %s, %s, %s, %s) RETURNING buyer_id;",
                (name, email, password, contact, address)
            )
            user_id = cursor.fetchone()[0]
            session['user_id'] = user_id
            session['username'] = name
            session['role'] = 'buyer'
            logger.debug(f"Buyer registered: {user_id}")
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('buyer_dashboard'))

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Register error: {str(e)}")
        return render_template('index.html', error=str(e))
    finally:
        if conn:
            cursor.close()
            conn.close()

@app.route('/farmer_dashboard')
def farmer_dashboard():
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to farmer_dashboard")
        return redirect('/')
    session['farmer_id'] = session['user_id']
    return render_template('farmer_dashboard.html', username=session.get('username'))

@app.route('/profile')
def profile():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect('/')
    farmer_id = session['user_id']
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM farmer WHERE farmer_id = %s", (farmer_id,))
    farmer = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('profile.html', farmer=farmer)

@app.route('/my_crops')
def my_crops():
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to my_crops")
        return redirect('/')
    farmer_id = session['user_id']
    logger.debug(f"Session user_id (farmer_id) in my_crops: {farmer_id}")
    conn = None
    try:
        conn = connect_db()
        if conn is None:
            return render_template('my_crops.html', results=[], crop_names=[], land_ids=[], error='Database connection failed.')
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                h.harvest_id,
                c.crop_id,
                c.crop_name,
                h.land_id,
                h.area_used_in_acres,
                h.sowing_date,
                h.harvest_date,
                h.status,
                h.yield
            FROM 
                harvest h
            JOIN 
                grows g ON h.grow_id = g.grow_id AND g.farmer_id = %s
            JOIN 
                crop c ON g.crop_id = c.crop_id 
            ORDER BY 
                h.harvest_date DESC;
        """, (farmer_id,))
        results = cur.fetchall()
        logger.debug(f"my_crops data fetched: {results}")
        cur.execute("SELECT crop_name FROM crop ORDER BY crop_name;")
        crop_names = [row[0] for row in cur.fetchall()]
        logger.debug(f"Crop names fetched: {crop_names}")
        cur.execute("SELECT land_id FROM land WHERE farmer_id = %s ORDER BY land_id;", (farmer_id,))
        land_ids = [row[0] for row in cur.fetchall()]
        logger.debug(f"Land IDs fetched for farmer {farmer_id}: {land_ids}")
        cur.close()
        return render_template('my_crops.html', results=results, crop_names=crop_names, land_ids=land_ids)
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error fetching crops: {str(e)}")
        return render_template('my_crops.html', results=[], crop_names=[], land_ids=[], error=f'Error fetching crops: {str(e)}')
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")

@app.route('/add_crop', methods=['POST'])
def add_crop():
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to add_crop")
        return redirect('/')
    farmer_id = session['user_id']
    logger.debug(f"Session user_id (farmer_id) in add_crop: {farmer_id}")
    data = request.form
    crop_name = data.get('crop_name')
    land_id = data.get('land_id')
    area_used_in_acres = data.get('area_used_in_acres')
    sowing_date = data.get('sowing_date')
    harvest_date = data.get('harvest_date')
    yield_value = data.get('yield', None)
    logger.debug(f"Form data received - crop_name: {crop_name}, land_id: {land_id}, area_used_in_acres: {area_used_in_acres}, sowing_date: {sowing_date}, harvest_date: {harvest_date}, initial yield: {yield_value}")
    if not all([crop_name, land_id, area_used_in_acres, sowing_date, harvest_date]):
        logger.error("Missing required form fields")
        return render_template('my_crops.html', results=[], crop_names=[], land_ids=[], error='All fields except Initial Yield are required.')
    try:
        area_used_in_acres = float(area_used_in_acres)
        yield_value = float(yield_value) if yield_value else None
        land_id = int(land_id)
    except ValueError as e:
        logger.error(f"Invalid form data type: {str(e)}")
        return render_template('my_crops.html', results=[], crop_names=[], land_ids=[], error=f'Invalid input: {str(e)}')
    conn = None
    try:
        conn = connect_db()
        if conn is None:
            logger.error("Database connection failed")
            return render_template('my_crops.html', results=[], crop_names=[], land_ids=[], error='Database connection failed.')
        cur = conn.cursor()
        cur.execute("SELECT crop_id FROM crop WHERE crop_name = %s;", (crop_name,))
        crop_id = cur.fetchone()
        if not crop_id:
            cur.execute("INSERT INTO crop (crop_name) VALUES (%s) RETURNING crop_id;", (crop_name,))
            crop_id = cur.fetchone()[0]
        else:
            crop_id = crop_id[0]
        logger.debug(f"Retrieved or inserted crop_id: {crop_id} for crop_name: {crop_name}")
        cur.execute("SELECT land_id FROM land WHERE land_id = %s AND farmer_id = %s;", (land_id, farmer_id))
        land_record = cur.fetchone()
        if not land_record:
            logger.error(f"Invalid land_id {land_id} for farmer_id {farmer_id}")
            raise ValueError("Invalid land_id for this farmer or land does not exist.")
        cur.execute("""
            SELECT grow_id, total_quantity_present 
            FROM grows 
            WHERE farmer_id = %s AND crop_id = %s;
        """, (farmer_id, crop_id))
        grow_record = cur.fetchone()
        if grow_record:
            grow_id = grow_record[0]
            logger.debug(f"Existing grow_id found: {grow_id}")
        else:
            cur.execute("""
                INSERT INTO grows (farmer_id, crop_id, total_quantity_present)
                VALUES (%s, %s, 0)
                RETURNING grow_id;
            """, (farmer_id, crop_id))
            grow_id = cur.fetchone()[0]
            logger.debug(f"Inserted new grow_id: {grow_id} with total_quantity_present: 0")
        cur.execute("""
            INSERT INTO harvest (grow_id, land_id, area_used_in_acres, sowing_date, harvest_date, yield)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING harvest_id;
        """, (grow_id, land_id, area_used_in_acres, sowing_date, harvest_date, yield_value))
        harvest_id = cur.fetchone()[0]
        logger.debug(f"Inserted into harvest with harvest_id: {harvest_id} for grow_id: {grow_id}")
        cur.execute("SELECT COUNT(*) FROM grows WHERE grow_id = %s AND farmer_id = %s;", (grow_id, farmer_id))
        grows_count = cur.fetchone()[0]
        logger.debug(f"Verification - grows table count for grow_id {grow_id}: {grows_count}")
        cur.execute("SELECT COUNT(*) FROM harvest WHERE harvest_id = %s;", (harvest_id,))
        harvest_count = cur.fetchone()[0]
        logger.debug(f"Verification - harvest table count for harvest_id {harvest_id}: {harvest_count}")
        if grows_count == 0 or harvest_count == 0:
            logger.error("Insert verification failed: Record not found in grows or harvest table")
            raise ValueError("Failed to verify insert: Record not found in database.")
        conn.commit()
        cur.close()
        logger.debug("Crop added successfully, redirecting to my_crops")
        return redirect(url_for('my_crops', message='Crop added successfully'))
    except Exception as e:
        if conn:
            conn.rollback()
            logger.debug("Transaction rolled back due to error")
        logger.error(f"Add crop error: {str(e)}")
        return render_template('my_crops.html', results=[], crop_names=[], land_ids=[], error=f'Add crop error: {str(e)}')
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")

@app.route('/update_crop/<int:harvest_id>', methods=['POST'])
def updateCrop(harvest_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to update_crop")
        return redirect('/')
    farmer_id = session['user_id']
    logger.debug(f"Session user_id (farmer_id) in update_crop: {farmer_id}")
    data = request.form
    crop_name = data['crop_name']
    land_id = data['land_id']
    area_used_in_acres = data['area_used_in_acres']
    sowing_date = data['sowing_date']
    harvest_date = data['harvest_date']
    yield_value = data.get('yield', None)
    yield_value = float(yield_value) if yield_value else None
    area_used_in_acres = float(area_used_in_acres)
    logger.debug(f"Updating crop - harvest_id: {harvest_id}, crop_name: {crop_name}, land_id: {land_id}, area_used_in_acres: {area_used_in_acres}, sowing_date: {sowing_date}, harvest_date: {harvest_date}, yield: {yield_value}")
    conn = None
    try:
        conn = connect_db()
        if conn is None:
            return render_template('my_crops.html', results=[], crop_names=[], land_ids=[], error='Database connection failed.')
        cur = conn.cursor()
        cur.execute("SELECT crop_id FROM crop WHERE crop_name = %s;", (crop_name,))
        crop_id = cur.fetchone()
        if not crop_id:
            cur.execute("INSERT INTO crop (crop_name) VALUES (%s) RETURNING crop_id;", (crop_name,))
            crop_id = cur.fetchone()[0]
        else:
            crop_id = crop_id[0]
        logger.debug(f"Retrieved or inserted crop_id: {crop_id} for crop_name: {crop_name}")
        cur.execute("SELECT land_id FROM land WHERE land_id = %s AND farmer_id = %s;", (land_id, farmer_id))
        if not cur.fetchone():
            raise ValueError("Invalid land_id for this farmer.")
        cur.execute("SELECT grow_id FROM harvest WHERE harvest_id = %s;", (harvest_id,))
        grow_id = cur.fetchone()
        if not grow_id:
            raise ValueError("No corresponding harvest record found for this harvest_id.")
        grow_id = grow_id[0]
        cur.execute("""
            UPDATE harvest
            SET land_id = %s, area_used_in_acres = %s, sowing_date = %s, harvest_date = %s, yield = %s
            WHERE harvest_id = %s;
        """, (land_id, area_used_in_acres, sowing_date, harvest_date, yield_value, harvest_id))
        if cur.rowcount == 0:
            raise ValueError("No harvest record found to update.")
        cur.execute("""
            UPDATE grows
            SET crop_id = %s
            WHERE grow_id = %s AND farmer_id = %s;
        """, (crop_id, grow_id, farmer_id))
        if cur.rowcount == 0:
            raise ValueError("No grows record found to update or you don't have permission.")
        conn.commit()
        cur.close()
        return redirect(url_for('my_crops', message='Crop updated successfully'))
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Update crop error: {str(e)}")
        return render_template('my_crops.html', results=[], crop_names=[], land_ids=[], error=f'Update crop error: {str(e)}')
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")

@app.route('/delete_crop/<int:harvest_id>', methods=['POST'])
def delete_crop(harvest_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to delete_crop")
        return redirect('/')
    farmer_id = session['user_id']
    logger.debug(f"Session user_id (farmer_id) in delete_crop: {farmer_id}")
    conn = None
    try:
        conn = connect_db()
        if conn is None:
            logger.error("Database connection failed")
            return render_template('my_crops.html', results=[], crop_names=[], land_ids=[], error='Database connection failed.')
        cur = conn.cursor()
        cur.execute("SELECT grow_id FROM harvest WHERE harvest_id = %s;", (harvest_id,))
        grow_id = cur.fetchone()
        if not grow_id:
            logger.error(f"No harvest record found for harvest_id {harvest_id}")
            raise ValueError("Harvest record not found or you don't have permission to delete it.")
        grow_id = grow_id[0]
        logger.debug(f"Found grow_id: {grow_id} for harvest_id: {harvest_id}")
        cur.execute("DELETE FROM harvest WHERE harvest_id = %s AND grow_id IN (SELECT grow_id FROM grows WHERE farmer_id = %s);", (harvest_id, farmer_id))
        if cur.rowcount == 0:
            logger.error(f"Failed to delete harvest for harvest_id {harvest_id} and farmer_id {farmer_id}")
            raise ValueError("Failed to delete harvest record or you don't have permission.")
        logger.debug(f"Deleted {cur.rowcount} rows from harvest for harvest_id: {harvest_id}")
        cur.execute("SELECT COUNT(*) FROM harvest WHERE grow_id = %s;", (grow_id,))
        if cur.fetchone()[0] == 0:
            cur.execute("DELETE FROM grows WHERE grow_id = %s AND farmer_id = %s;", (grow_id, farmer_id))
            logger.debug(f"Deleted {cur.rowcount} rows from grows for grow_id: {grow_id}")
        conn.commit()
        cur.close()
        logger.debug("Crop deleted successfully, redirecting to my_crops")
        return redirect(url_for('my_crops', message='Crop deleted successfully'))
    except Exception as e:
        if conn:
            conn.rollback()
            logger.debug("Transaction rolled back due to error")
        logger.error(f"Delete crop error: {str(e)}")
        return render_template('my_crops.html', results=[], crop_names=[], land_ids=[], error=f'Delete crop error: {str(e)}')
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")

@app.route('/yield_status')
def yield_status():
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to yield_status")
        return redirect('/')
    farmer_id = session['user_id']
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            c.crop_id,
            c.crop_name,
            g.total_quantity_present
        FROM 
            grows g
        JOIN 
            crop c ON g.crop_id = c.crop_id
        WHERE 
            g.farmer_id = %s AND
            g.total_quantity_present > 0;
    """, (farmer_id,))
    results = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('yield_status.html', data=results)

@app.route('/my_inventory')
def my_inventory():
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to my_inventory")
        return redirect('/')
    farmer_id = session['user_id']
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.maintains_id, m.inventory_id, i.inventory_name, mk.market_name, m.purchase_date, 
               mp.expiry_date, m.quantity_present, m.min_quantity,
               CASE
                   WHEN COALESCE(mp.expiry_date, CURRENT_DATE) < CURRENT_DATE THEN 'Expired'
                   WHEN COALESCE(mp.expiry_date, CURRENT_DATE + INTERVAL '30 days') <= CURRENT_DATE + INTERVAL '30 days' THEN 'Expiring Soon'
                   ELSE 'Valid'
               END AS validity
        FROM maintains m
        JOIN inventory i ON m.inventory_id = i.inventory_id
        JOIN market mk ON m.market_id = mk.market_id
        LEFT JOIN market_price mp ON m.inventory_id = mp.inventory_id AND m.market_id = mp.market_id
        WHERE m.farmer_id = %s;
    """, (farmer_id,))
    data = cur.fetchall()
    logger.debug(f"my_inventory data fetched: {data}")
    cur.close()
    conn.close()
    message = request.args.get('message')
    return render_template('my_inventory.html', data=data, message=message)

@app.route('/my_land')
def my_land():
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to my_land")
        return redirect('/')
    farmer_id = session['user_id']
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            l.land_id,
            l.land_size,
            l.soil_type,
            l.location,
            l.ownership
        FROM 
            land l
        WHERE 
            l.farmer_id = %s;
    """, (farmer_id,))
    lands = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('my_land.html', data=lands)


@app.route('/add_land', methods=['POST'])
def add_land():
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to add_land")
        return redirect('/')
    farmer_id = session['user_id']
    data = request.form
    land_id = data['land_id']
    size = data['size']
    soil_type = data['soil_type']
    location = data['location']
    ownership = data['ownership']
    try:
        conn = connect_db()
        if conn is None:
            return render_template('my_land.html', data=[], error='Database connection failed.')
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO land (land_id, farmer_id, land_size, soil_type, location, ownership)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (land_id, farmer_id, size, soil_type, location, ownership))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('my_land'))
    except Exception as e:
        if conn:
            conn.rollback()
        return render_template('my_land.html', data=[], error=f'Add land error: {str(e)}')

@app.route('/update_land/<int:land_id>', methods=['POST'])
def update_land(land_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to update_land")
        return redirect('/')
    farmer_id = session['user_id']
    data = request.form
    size = data['size']
    soil_type = data['soil_type']
    location = data['location']
    ownership = data['ownership']
    try:
        conn = connect_db()
        if conn is None:
            return render_template('my_land.html', data=[], error='Database connection failed.')
        cur = conn.cursor()
        cur.execute("""
            UPDATE land
            SET land_size = %s, soil_type = %s, location = %s, ownership = %s
            WHERE land_id = %s AND farmer_id = %s;
        """, (size, soil_type, location, ownership, land_id, farmer_id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('my_land'))
    except Exception as e:
        if conn:
            conn.rollback()
        return render_template('my_land.html', data=[], error=f'Update land error: {str(e)}')

@app.route('/delete_land/<int:land_id>', methods=['POST'])
def delete_land(land_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to delete_land")
        return redirect('/')
    farmer_id = session['user_id']
    logger.debug(f"Attempting to delete land_id={land_id} for farmer_id={farmer_id}")
    conn = None
    try:
        conn = connect_db()
        if conn is None:
            logger.error("Database connection failed")
            return render_template('my_land.html', data=[], error='Database connection failed.')
        cur = conn.cursor()
        cur.execute("DELETE FROM land WHERE land_id = %s AND farmer_id = %s;", (land_id, farmer_id))
        affected_rows = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        if affected_rows == 0:
            logger.warning(f"No land found with land_id={land_id} and farmer_id={farmer_id}")
            conn = connect_db()
            if conn:
                cur = conn.cursor()
                cur.execute("SELECT land_id, land_size, soil_type, location, ownership FROM land WHERE farmer_id = %s;", (farmer_id,))
                data = cur.fetchall()
                cur.close()
                conn.close()
                return render_template('my_land.html', data=data, error='No land found with the specified ID or you do not have permission to delete it.')
            return render_template('my_land.html', data=[], error='Database connection failed.')
        logger.info(f"Successfully deleted land_id={land_id}")
        return redirect(url_for('my_land'))
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logger.error(f"Delete land error for land_id={land_id}: {str(e)}")
        conn = connect_db()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT land_id, land_size, soil_type, location, ownership FROM land WHERE farmer_id = %s;", (farmer_id,))
            data = cur.fetchall()
            cur.close()
            conn.close()
            return render_template('my_land.html', data=data, error=f'Delete land error: {str(e)}')
        return render_template('my_land.html', data=[], error=f'Delete land error: {str(e)}')

@app.route('/add_inventory', methods=['POST'])
def add_inventory():
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to add_inventory")
        return redirect('/')
    farmer_id = session['user_id']
    logger.debug(f"Processing add_inventory for farmer_id={farmer_id}")
    data = request.form
    inventory_name = data['inventory_name'].strip()
    market = data['market'].strip()
    purchase_date_str = data['purchase_date']
    quantity_present = data['quantity_present']
    min_quantity = data['min_quantity']
    conn = None
    try:
        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
        logger.debug(f"Parsed purchase_date: {purchase_date}")
        quantity_present = float(quantity_present)
        min_quantity = float(min_quantity)
        if quantity_present <= 0 or min_quantity < 0:
            raise ValueError("Quantity must be positive and minimum quantity cannot be negative.")
        logger.debug(f"Validated data: {inventory_name}, {market}, {purchase_date}, {quantity_present}, {min_quantity}")
        conn = connect_db()
        if conn is None:
            raise Exception('Database connection failed.')
        logger.debug("Database connection established")
        cur = conn.cursor()
        cur.execute("SELECT inventory_id FROM inventory WHERE LOWER(inventory_name) = LOWER(%s);", (inventory_name,))
        result = cur.fetchone()
        if not result:
            raise ValueError(f"Inventory {inventory_name} not found in database. Please use an existing inventory name.")
        inventory_id = result[0]
        logger.debug(f"Found existing inventory_id={inventory_id} for {inventory_name}")
        cur.execute("SELECT market_id FROM market WHERE LOWER(market_name) = LOWER(%s);", (market,))
        result = cur.fetchone()
        if not result:
            raise ValueError(f"Market {market} not found in database. Please use an existing market name.")
        market_id = result[0]
        logger.debug(f"Found existing market_id={market_id} for {market}")
        cur.execute("""
            SELECT maintains_id FROM maintains 
            WHERE farmer_id = %s AND inventory_id = %s AND market_id = %s AND purchase_date = %s;
        """, (farmer_id, inventory_id, market_id, purchase_date))
        if cur.fetchone():
            logger.warning(f"Duplicate entry found for farmer_id={farmer_id}, inventory_id={inventory_id}, market_id={market_id}, purchase_date={purchase_date}")
            cur.close()
            conn.close()
            return redirect(url_for('my_inventory'))
        logger.debug(f"Executing maintains insert for farmer_id={farmer_id}, inventory_id={inventory_id}, market_id={market_id}")
        cur.execute("""
            INSERT INTO maintains (farmer_id, inventory_id, market_id, purchase_date, quantity_present, min_quantity, unit, valid, last_accessed)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_DATE)
            RETURNING maintains_id;
        """, (farmer_id, inventory_id, market_id, purchase_date, quantity_present, min_quantity, 'K', 'Y'))
        maintains_id = cur.fetchone()[0]
        logger.debug(f"Committed maintains insert with maintains_id={maintains_id}, inventory_id={inventory_id}, market_id={market_id}")
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('my_inventory', message='Inventory item added successfully'))
    except ValueError as ve:
        if conn:
            conn.rollback()
            logger.error(f"Rolled back transaction due to error: {str(ve)}")
        logger.error(f"Add inventory error: {str(ve)}")
        return render_template('my_inventory.html', data=[], error=f'Add inventory error: {str(ve)}')
    except Exception as e:
        if conn:
            conn.rollback()
            logger.error(f"Rolled back transaction due to error: {str(e)}")
        logger.error(f"Add inventory error: {str(e)}")
        return render_template('my_inventory.html', data=[], error=f'Add inventory error: {str(e)}')

@app.route('/update_inventory/<int:maintains_id>', methods=['POST'])
def update_inventory(maintains_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to update_inventory")
        return redirect('/')
    farmer_id = session['user_id']
    logger.debug(f"Processing update_inventory for maintains_id={maintains_id}, farmer_id={farmer_id}")
    data = request.form
    inventory_name = data['inventory_name'].strip()
    market = data['market'].strip()
    purchase_date_str = data['purchase_date']
    quantity_present = data['quantity_present']
    min_quantity = data['min_quantity']
    conn = None
    try:
        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
        logger.debug(f"Parsed purchase_date: {purchase_date}")
        quantity_present = float(quantity_present)
        min_quantity = float(min_quantity)
        if quantity_present <= 0 or min_quantity < 0:
            raise ValueError("Quantity must be positive and minimum quantity cannot be negative.")
        logger.debug(f"Validated data: {inventory_name}, {market}, {purchase_date}, {quantity_present}, {min_quantity}")
        conn = connect_db()
        if conn is None:
            raise Exception('Database connection failed.')
        logger.debug("Database connection established")
        cur = conn.cursor()
        cur.execute("SELECT inventory_id FROM inventory WHERE LOWER(inventory_name) = LOWER(%s);", (inventory_name,))
        result = cur.fetchone()
        if not result:
            raise ValueError(f"Inventory {inventory_name} not found in database.")
        inventory_id = result[0]
        logger.debug(f"Found existing inventory_id={inventory_id} for {inventory_name}")
        cur.execute("SELECT market_id FROM market WHERE LOWER(market_name) = LOWER(%s);", (market,))
        result = cur.fetchone()
        if not result:
            raise ValueError(f"Market {market} not found in database.")
        market_id = result[0]
        logger.debug(f"Found existing market_id={market_id} for {market}")
        cur.execute("""
            UPDATE maintains 
            SET inventory_id = %s, market_id = %s, purchase_date = %s, 
                quantity_present = %s, min_quantity = %s, last_accessed = CURRENT_DATE
            WHERE maintains_id = %s AND farmer_id = %s;
        """, (inventory_id, market_id, purchase_date, quantity_present, min_quantity, maintains_id, farmer_id))
        if cur.rowcount == 0:
            raise ValueError("No inventory item found to update or you don't have permission.")
        conn.commit()
        logger.debug(f"Successfully updated maintains_id={maintains_id}")
        cur.close()
        conn.close()
        return redirect(url_for('my_inventory', message='Inventory item updated successfully'))
    except ValueError as ve:
        if conn:
            conn.rollback()
            logger.error(f"Rolled back transaction due to error: {str(ve)}")
        logger.error(f"Update inventory error: {str(ve)}")
        return render_template('my_inventory.html', data=[], error=f'Update inventory error: {str(ve)}')
    except Exception as e:
        if conn:
            conn.rollback()
            logger.error(f"Rolled back transaction due to error: {str(e)}")
        logger.error(f"Update inventory error: {str(e)}")
        return render_template('my_inventory.html', data=[], error=f'Update inventory error: {str(e)}')

@app.route('/delete_inventory/<int:maintains_id>', methods=['POST'])
def delete_inventory(maintains_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to delete_inventory")
        return redirect('/')
    farmer_id = session['user_id']
    logger.debug(f"Processing delete_inventory for maintains_id={maintains_id}, farmer_id={farmer_id}")
    conn = None
    try:
        conn = connect_db()
        if conn is None:
            return redirect(url_for('my_inventory', error='Database connection failed.'))
        logger.debug("Database connection established")
        cur = conn.cursor()
        cur.execute("DELETE FROM maintains WHERE maintains_id = %s AND farmer_id = %s;", (maintains_id, farmer_id))
        if cur.rowcount == 0:
            logger.warning(f"No row deleted for maintains_id={maintains_id}, farmer_id={farmer_id}")
            return redirect(url_for('my_inventory', error='No inventory item found to delete or you don\'t have permission.'))
        conn.commit()
        logger.debug(f"Successfully deleted maintains_id={maintains_id}")
        cur.close()
        conn.close()
        return redirect(url_for('my_inventory', message='Inventory item deleted successfully'))
    except Exception as e:
        if conn:
            conn.rollback()
            logger.error(f"Rolled back transaction due to error: {str(e)}")
        logger.error(f"Delete inventory error: {str(e)}")
        return redirect(url_for('my_inventory', error=f'Delete inventory error: {str(e)}'))

@app.route('/my_sales')
def my_sales():
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to my_sales")
        return redirect('/')
    farmer_id = session['user_id']
    logger.debug(f"Session user_id (farmer_id) in my_sales: {farmer_id}")
    conn = None
    try:
        conn = connect_db()
        if conn is None:
            return render_template('my_sales.html', data=[], error='Database connection failed.')
        cur = conn.cursor()
        cur.execute("""
            SELECT s.sale_id, c.crop_id, c.crop_name, s.quantity_selling, s.amount_of_sale
            FROM sale s
            JOIN grows g ON s.grow_id = g.grow_id
            JOIN crop c ON g.crop_id = c.crop_id
            WHERE g.farmer_id = %s;
        """, (farmer_id,))
        data = cur.fetchall()
        logger.debug(f"my_sales data fetched: {data}")
        cur.close()
        return render_template('my_sales.html', data=data)
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error fetching sales: {str(e)}")
        return render_template('my_sales.html', data=[], error=f'Error fetching sales: {str(e)}')
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")

@app.route('/add_sale', methods=['POST'])
def add_sale():
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to add_sale")
        return redirect('/')
    farmer_id = session['user_id']
    logger.debug(f"Session user_id (farmer_id) in add_sale: {farmer_id}")
    data = request.form
    crop_name = data['crop_name']
    quantity_selling = data['quantity_selling']
    amount_sale = data['amount_sale']
    logger.debug(f"Adding sale - crop_name: {crop_name}, quantity_selling: {quantity_selling}, amount_of_sale: {amount_sale}")
    conn = None
    try:
        conn = connect_db()
        if conn is None:
            return render_template('my_sales.html', data=[], error='Database connection failed.')
        cur = conn.cursor()
        cur.execute("SELECT crop_id FROM crop WHERE crop_name = %s;", (crop_name,))
        crop_id = cur.fetchone()
        if not crop_id:
            cur.execute("INSERT INTO crop (crop_name) VALUES (%s) RETURNING crop_id;", (crop_name,))
            crop_id = cur.fetchone()[0]
        else:
            crop_id = crop_id[0]
        logger.debug(f"Retrieved or inserted crop_id: {crop_id} for crop_name: {crop_name}")
        cur.execute("SELECT grow_id FROM grows WHERE farmer_id = %s AND crop_id = %s;", (farmer_id, crop_id))
        grow_id = cur.fetchone()
        if not grow_id:
            cur.execute("INSERT INTO grows (farmer_id, crop_id, total_quantity_present) VALUES (%s, %s, 0) RETURNING grow_id;", (farmer_id, crop_id))
            grow_id = cur.fetchone()[0]
        else:
            grow_id = grow_id[0]
        logger.debug(f"Retrieved or inserted grow_id: {grow_id} for farmer_id: {farmer_id}, crop_id: {crop_id}")
        cur.execute("""
            INSERT INTO sale (grow_id, quantity_selling, unit, amount_of_sale)
            VALUES (%s, %s, %s, %s) RETURNING sale_id;
        """, (grow_id, quantity_selling, 'K', amount_sale))
        sale_id = cur.fetchone()[0]
        logger.debug(f"Successfully inserted sale with sale_id: {sale_id}, grow_id: {grow_id}, quantity_selling: {quantity_selling}, amount_of_sale: {amount_sale}")
        conn.commit()
        cur.close()
        return redirect(url_for('my_sales', message='Sale added successfully'))
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Add sale error: {str(e)}")
        return render_template('my_sales.html', data=[], error=f'Add sale error: {str(e)}')
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")

@app.route('/update_sale/<int:sale_id>', methods=['POST'])
def update_sale(sale_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to update_sale")
        return redirect('/')
    farmer_id = session['user_id']
    logger.debug(f"Session user_id (farmer_id) in update_sale: {farmer_id}")
    data = request.form
    crop_id = data.get('crop_id', '').strip()
    crop_name = data.get('crop_name', '').strip()
    quantity_selling = data.get('quantity_selling', '').strip()
    amount_sale = data.get('amount_sale', '').strip()
    logger.debug(f"Updating sale - sale_id: {sale_id}, crop_id: {crop_id}, crop_name: {crop_name}, quantity_selling: {quantity_selling}, amount_of_sale: {amount_sale}")
    if not all([crop_id, crop_name, quantity_selling, amount_sale]):
        return render_template('my_sales.html', data=[], error='All fields are required.')
    conn = None
    try:
        conn = connect_db()
        if conn is None:
            return render_template('my_sales.html', data=[], error='Database connection failed.')
        cur = conn.cursor()
        cur.execute("SELECT crop_id FROM crop WHERE crop_name = %s;", (crop_name,))
        result = cur.fetchone()
        if not result:
            cur.execute("INSERT INTO crop (crop_name) VALUES (%s) RETURNING crop_id;", (crop_name,))
            crop_id = cur.fetchone()[0]
        else:
            crop_id = result[0]
        logger.debug(f"Retrieved or inserted crop_id: {crop_id} for crop_name: {crop_name}")
        cur.execute("SELECT grow_id, total_quantity_present FROM grows WHERE farmer_id = %s AND crop_id = %s;", (farmer_id, crop_id))
        grow_result = cur.fetchone()
        if not grow_result:
            cur.execute("INSERT INTO grows (farmer_id, crop_id, total_quantity_present) VALUES (%s, %s, 0) RETURNING grow_id;", (farmer_id, crop_id))
            grow_id = cur.fetchone()[0]
            total_quantity_present = 0
        else:
            grow_id, total_quantity_present = grow_result
        logger.debug(f"Retrieved or inserted grow_id: {grow_id} for farmer_id: {farmer_id}, crop_id: {crop_id}, total_quantity_present: {total_quantity_present}")
        quantity_selling = float(quantity_selling)
        cur.execute("SELECT quantity_selling FROM sale WHERE sale_id = %s;", (sale_id,))
        current_quantity_selling = cur.fetchone()[0]
        quantity_diff = quantity_selling - current_quantity_selling
        if quantity_diff > 0 and total_quantity_present < quantity_diff:
            cur.close()
            return render_template('my_sales.html', data=[], error=f'Insufficient quantity in inventory for {crop_name}. Available: {total_quantity_present}, Additional Requested: {quantity_diff}')
        cur.execute("""
            UPDATE sale
            SET grow_id = %s, quantity_selling = %s, unit = %s, amount_of_sale = %s
            WHERE sale_id = %s AND grow_id IN (
                SELECT grow_id FROM grows WHERE farmer_id = %s
            );
        """, (grow_id, quantity_selling, 'K', amount_sale, sale_id, farmer_id))
        if cur.rowcount == 0:
            raise ValueError("No sale found to update or you don't have permission.")
        conn.commit()
        cur.close()
        return redirect(url_for('my_sales', message='Sale updated successfully'))
    except (psycopg2.Error, ValueError) as e:
        if conn:
            conn.rollback()
        logger.error(f"Update sale error: {str(e)}")
        return render_template('my_sales.html', data=[], error=f'Update sale error: {str(e)}')
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")

@app.route('/delete_sale/<int:sale_id>', methods=['POST'])
def delete_sale(sale_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to delete_sale")
        return redirect('/')
    farmer_id = session['user_id']
    logger.debug(f"Session user_id (farmer_id) in delete_sale: {farmer_id}")
    conn = None
    try:
        conn = connect_db()
        if conn is None:
            return redirect(url_for('my_sales', error='Database connection failed.'))
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM sale
            WHERE sale_id = %s AND grow_id IN (
                SELECT grow_id FROM grows WHERE farmer_id = %s
            );
        """, (sale_id, farmer_id))
        if cur.rowcount == 0:
            logger.warning(f"No sale deleted for sale_id: {sale_id}, farmer_id: {farmer_id}")
            return redirect(url_for('my_sales', error='No sale found to delete or you don\'t have permission.'))
        logger.debug(f"Successfully deleted sale with sale_id: {sale_id}")
        conn.commit()
        cur.close()
        return redirect(url_for('my_sales', message='Sale deleted successfully'))
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Delete sale error: {str(e)}")
        return redirect(url_for('my_sales', error=f'Delete sale error: {str(e)}'))
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed") 

@app.route('/buyer_dashboard')
def buyer_dashboard():
    if 'user_id' not in session or session.get('role') != 'buyer':
        logger.warning("Unauthorized access to buyer_dashboard")
        return redirect('/')
    buyer_id = session['user_id']
    logger.debug(f"Fetching buyer details for buyer_id: {buyer_id}")
    conn = None
    try:
        conn = connect_db()
        if conn is None:
            logger.error("Database connection failed")
            return render_template('buyer_dashboard.html', buyer=None, error='Database connection failed.')
        cur = conn.cursor()
        cur.execute("SELECT buyer_id, buyer_name, email_id, contact_no, address FROM buyer WHERE buyer_id = %s;", (buyer_id,))
        buyer = cur.fetchone()
        if not buyer:
            logger.warning(f"No buyer record found for buyer_id: {buyer_id}")
            return render_template('buyer_dashboard.html', buyer=None, error='No buyer profile found. Please contact support or complete your profile.')
        logger.debug(f"Buyer details fetched: {buyer}")
        cur.close()
        return render_template('buyer_dashboard.html', buyer=buyer)
    except Exception as e:
        logger.error(f"Error fetching buyer details: {str(e)}")
        return render_template('buyer_dashboard.html', buyer=None, error=f'Error fetching buyer details: {str(e)}')
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")

@app.route('/purchase', methods=['GET', 'POST'])
def purchase():
    if 'user_id' not in session or session.get('role') != 'buyer':
        logger.warning("Unauthorized access to purchase")
        return redirect('/')
    buyer_id = session['user_id']
    conn = None
    try:
        conn = connect_db()
        if conn is None:
            logger.error("Database connection failed")
            return render_template('purchase.html', error='Database connection failed.', requirements=[], crops=[])
        cur = conn.cursor()
        
        # Fetch all crops for the dropdown
        cur.execute("SELECT crop_id, crop_name FROM crop ORDER BY crop_name;")
        crops = cur.fetchall()

        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'add_requirement':
                crop_id = request.form.get('crop_id')
                quantity = request.form.get('quantity')
                unit = request.form.get('unit', 'K')
                min_price = request.form.get('min_price', 0)
                max_price = request.form.get('max_price', 999999)
                
                try:
                    min_price = float(min_price)
                    max_price = float(max_price)
                    quantity = float(quantity)
                    if min_price < 0 or max_price < min_price or quantity <= 0:
                        raise ValueError("Invalid input: Prices must be non-negative, max_price >= min_price, and quantity > 0.")
                except ValueError as e:
                    cur.close()
                    conn.close()
                    return render_template('purchase.html', error=f"Invalid numeric input: {str(e)}", requirements=[], crops=crops)
                
                try:
                    cur.execute("""
                        INSERT INTO buyer_requirements (buyer_id, crop_id, quantity, unit, min_afford, max_afford)
                        VALUES (%s, %s, %s, %s, %s, %s) RETURNING required_id;
                    """, (buyer_id, crop_id, quantity, unit, min_price, max_price))
                    required_id = cur.fetchone()[0]
                    conn.commit()
                    logger.debug(f"Added buyer requirement: required_id={required_id}, buyer_id={buyer_id}")
                except Exception as e:
                    conn.rollback()
                    cur.close()
                    conn.close()
                    return render_template('purchase.html', error=f"Failed to add requirement: {str(e)}", requirements=[], crops=crops)

            # Fetch requirements after adding (or on GET)
            cur.execute("""
                SELECT br.required_id, c.crop_name, br.quantity, br.unit, br.min_afford, br.max_afford
                FROM buyer_requirements br
                JOIN crop c ON br.crop_id = c.crop_id
                WHERE br.buyer_id = %s
                ORDER BY br.required_id DESC;
            """, (buyer_id,))
            requirements = cur.fetchall()
            
            cur.close()
            conn.close()
            return render_template('purchase.html', requirements=requirements, crops=crops, message='Requirement added successfully' if action == 'add_requirement' else None)

        else:  # GET request
            cur.execute("""
                SELECT br.required_id, c.crop_name, br.quantity, br.unit, br.min_afford, br.max_afford
                FROM buyer_requirements br
                JOIN crop c ON br.crop_id = c.crop_id
                WHERE br.buyer_id = %s
                ORDER BY br.required_id DESC;
            """, (buyer_id,))
            requirements = cur.fetchall()
            cur.close()
            conn.close()
            return render_template('purchase.html', requirements=requirements, crops=crops)

    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logger.error(f"Purchase error: {str(e)}")
        return render_template('purchase.html', error=f"Error: {str(e)}", requirements=[], crops=[])

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/fetch_sales/<int:required_id>', methods=['GET'])
def fetch_sales(required_id):
    if 'user_id' not in session or session.get('role') != 'buyer':
        logger.warning("Unauthorized access to fetch_sales")
        return jsonify({'error': 'Unauthorized access.'}), 403
    buyer_id = session['user_id']
    conn = None
    try:
        logger.info(f"Processing fetch_sales for required_id={required_id}, buyer_id={buyer_id}")
        conn = connect_db()
        if conn is None:
            logger.error("Database connection failed")
            return jsonify({'error': 'Database connection failed.'}), 500
        cur = conn.cursor()
        cur.execute("SELECT buyer_id FROM buyer_requirements WHERE required_id = %s;", (required_id,))
        result = cur.fetchone()
        if not result or result[0] != buyer_id:
            logger.warning(f"Unauthorized access to required_id {required_id} by buyer_id {buyer_id}")
            cur.close()
            conn.close()
            return jsonify({'error': 'Unauthorized access.'}), 403
        cur.execute("""
            SELECT 
                s.sale_id, 
                c.crop_name, 
                f.farmer_name, 
                s.quantity_selling, 
                s.unit, 
                s.amount_of_sale,
                c.crop_id,
                f.farmer_id
            FROM sale s
            JOIN grows g ON s.grow_id = g.grow_id
            JOIN crop c ON g.crop_id = c.crop_id
            JOIN farmer f ON g.farmer_id = f.farmer_id
            JOIN buyer_requirements br ON br.required_id = %s
            WHERE g.crop_id = br.crop_id
            AND s.amount_of_sale BETWEEN br.min_afford AND br.max_afford
            AND s.quantity_selling >= br.quantity;
        """, (required_id,))
        sales = cur.fetchall()
        logger.debug(f"Fetched {len(sales)} sales for required_id={required_id}")
        cur.close()
        conn.close()
        sales_data = [
            {
                'sale_id': row[0],
                'crop_name': row[1],
                'farmer_name': row[2],
                'quantity_selling': float(row[3]),
                'unit': row[4],
                'amount_of_sale': float(row[5]),
                'crop_id': row[6],
                'farmer_id': row[7]
            } for row in sales
        ]
        return jsonify({'sales': sales_data})
    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Fetch sales error for required_id={required_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500 

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session or session.get('role') != 'buyer':
        return jsonify({'error': 'Unauthorized access.'}), 403
    buyer_id = session['user_id']
    
    data = request.form
    sale_id = int(data.get('sale_id'))
    required_id = int(data.get('required_id'))
    crop_id = int(data.get('crop_id'))
    crop_name = data.get('crop_name')
    farmer_id = int(data.get('farmer_id'))
    farmer_name = data.get('farmer_name')
    quantity = float(data.get('quantity'))
    amount_of_sale = float(data.get('amount_of_sale'))
    
    if 'cart' not in session:
        session['cart'] = []
    
    for item in session['cart']:
        if item['sale_id'] == sale_id:
            return jsonify({'error': 'Item already in cart.'}), 400
    
    cart_item = {
        'sale_id': sale_id,
        'required_id': required_id,
        'crop_id': crop_id,
        'crop_name': crop_name,
        'farmer_id': farmer_id,
        'farmer_name': farmer_name,
        'quantity': quantity,
        'amount_of_sale': amount_of_sale,
        'unit': 'Kg'
    }
    session['cart'].append(cart_item)
    session.modified = True
    logger.info(f"Added to cart: sale_id={sale_id}, buyer_id={buyer_id}")
    return jsonify({'message': 'Item added to cart successfully.'})



@app.route('/delete_requirement/<int:required_id>', methods=['POST'])
def delete_requirement(required_id):
    if 'user_id' not in session or session.get('role') != 'buyer':
        logger.warning("Unauthorized access to delete_requirement")
        return redirect('/')
    buyer_id = session['user_id']
    conn = None
    try:
        conn = connect_db()
        if conn is None:
            logger.error("Database connection failed")
            return redirect(url_for('purchase', error='Database connection failed.'))
        cur = conn.cursor()
        cur.execute("DELETE FROM buyer_requirements WHERE required_id = %s AND buyer_id = %s;", (required_id, buyer_id))
        if cur.rowcount == 0:
            logger.warning(f"No requirement deleted for required_id: {required_id}, buyer_id: {buyer_id}")
            cur.close()
            conn.close()
            return redirect(url_for('purchase', error='Requirement not found or you don\'t have permission.'))
        conn.commit()
        cur.close()
        conn.close()
        logger.debug(f"Successfully deleted requirement with required_id: {required_id}")
        return redirect(url_for('purchase', message='Requirement deleted successfully'))
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logger.error(f"Delete requirement error: {str(e)}")
        return redirect(url_for('purchase', error=f'Delete requirement error: {str(e)}'))

@app.route('/cart', methods=['GET'])
def cart():
    if 'user_id' not in session or session.get('role') != 'buyer':
        logger.warning("Unauthorized access to cart")
        return redirect('/')
    cart_items = session.get('cart', [])
    total_amount = sum(item['amount_of_sale'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total_amount=total_amount)


@app.route('/delete_cart_item/<int:sale_id>', methods=['POST'])
def delete_cart_item(sale_id):
    if 'user_id' not in session or session.get('role') != 'buyer':
        return jsonify({'error': 'Unauthorized access.'}), 403
    if 'cart' not in session:
        return jsonify({'error': 'Cart is empty.'}), 400
    
    session['cart'] = [item for item in session['cart'] if item['sale_id'] != sale_id]
    session.modified = True
    logger.info(f"Deleted cart item: sale_id={sale_id}, buyer_id={session['user_id']}")
    return jsonify({'message': 'Item removed from cart.'})


@app.route('/proceed_payment', methods=['POST'])
def proceed_payment():
    if 'user_id' not in session or session.get('role') != 'buyer':
        logger.warning("Unauthorized access to proceed_payment")
        return redirect('/')
    buyer_id = session['user_id']
    cart_items = session.get('cart', [])
    
    if not cart_items:
        return render_template('cart.html', error="Cart is empty.", cart_items=[])
    
    conn = None
    try:
        conn = connect_db()
        if conn is None:
            return render_template('cart.html', error="Database connection failed.", cart_items=cart_items)
        cur = conn.cursor()
        
        for item in cart_items:
            if item['amount_of_sale'] is None:
                raise ValueError(f"Invalid amount_of_sale for sale_id {item['sale_id']}")
            cur.execute("""
                INSERT INTO purchase (sale_id, required_id, purchase_date, amount_paid)
                VALUES (%s, %s, CURRENT_DATE, %s)
            """, (item['sale_id'], item['required_id'], float(item['amount_of_sale'])))
        
        conn.commit()
        logger.info(f"Processed payment for {len(cart_items)} items, buyer_id={buyer_id}")
        
        session['cart'] = []
        session.modified = True
        
        cur.close()
        conn.close()
        return redirect('/buyer_transaction')
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logger.error(f"Payment error for buyer_id={buyer_id}: {str(e)}")
        return render_template('cart.html', error=f"Payment failed: {str(e)}", cart_items=cart_items)


@app.route('/buyer_transaction', methods=['GET'])
def buyer_transaction():
    if 'user_id' not in session or session.get('role') != 'buyer':
        logger.warning("Unauthorized access to buyer_transaction")
        return redirect('/')
    buyer_id = session['user_id']
    
    conn = None
    try:
        conn = connect_db()
        if conn is None:
            return render_template('buyer_transaction.html', error="Database connection failed.", transactions=[])
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                p.purchase_id,
                c.crop_name,
                f.farmer_name,
                br.quantity,
                br.unit,
                p.amount_paid,
                p.purchase_date
            FROM purchase p
            JOIN sale s ON p.sale_id = s.sale_id
            JOIN grows g ON s.grow_id = g.grow_id
            JOIN crop c ON g.crop_id = c.crop_id
            JOIN farmer f ON g.farmer_id = f.farmer_id
            JOIN buyer_requirements br ON p.required_id = br.required_id
            WHERE br.buyer_id = %s
            ORDER BY p.purchase_date DESC
        """, (buyer_id,))
        
        transactions = [
            {
                'purchase_id': row[0],
                'crop_name': row[1],
                'farmer_name': row[2],
                'quantity': float(row[3]),
                'unit': row[4],
                'amount_paid': float(row[5]),
                'purchase_date': row[6]
            } for row in cur.fetchall()
        ]
        
        cur.close()
        conn.close()
        return render_template('buyer_transaction.html', transactions=transactions)
    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Buyer transaction error for buyer_id={buyer_id}: {str(e)}")
        return render_template('buyer_transaction.html', error=f"Error fetching transactions: {str(e)}", transactions=[])
    
@app.route('/farmer_transaction', methods=['GET'])
def farmer_transaction():
    if 'user_id' not in session or session.get('role') != 'farmer':
        logger.warning("Unauthorized access to farmer_transaction")
        return redirect('/')
    farmer_id = session['user_id']
    
    conn = None
    try:
        conn = connect_db()
        if conn is None:
            return render_template('farmer_transaction.html', error="Database connection failed.", transactions=[])
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                p.purchase_id,
                c.crop_name,
                b.buyer_name,
                br.quantity,
                br.unit,
                p.amount_paid,
                p.purchase_date
            FROM purchase p
            JOIN sale s ON p.sale_id = s.sale_id
            JOIN grows g ON s.grow_id = g.grow_id
            JOIN crop c ON g.crop_id = c.crop_id
            JOIN buyer_requirements br ON p.required_id = br.required_id
            JOIN buyer b ON br.buyer_id = b.buyer_id
            WHERE g.farmer_id = %s
            ORDER BY p.purchase_date DESC
        """, (farmer_id,))
        
        transactions = [
            {
                'purchase_id': row[0],
                'crop_name': row[1],
                'buyer_name': row[2],
                'quantity': float(row[3]),
                'unit': row[4],
                'amount_paid': float(row[5]),
                'purchase_date': row[6]
            } for row in cur.fetchall()
        ]
        
        cur.close()
        conn.close()
        return render_template('farmer_transaction.html', transactions=transactions)
    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Farmer transaction error for farmer_id={farmer_id}: {str(e)}")
        return render_template('farmer_transaction.html', error=f"Error fetching transactions: {str(e)}", transactions=[])


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run()