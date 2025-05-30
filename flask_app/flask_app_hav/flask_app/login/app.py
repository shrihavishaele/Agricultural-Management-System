from flask import Flask, render_template, request, session
from db_config import connect_db 


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session

@app.route('/')
def dashboard():
    # Simulate a farmer_id from session or login (you can adjust later)
    session['farmer_id'] = 1
    return render_template('dashboard.html', farmer_name="Farmer 1")

@app.route('/profile')
def profile():
    farmer_id = session.get('farmer_id') 
    conn = connect_db()
    cur = conn.cursor() 
    cur.execute("SELECT * FROM farmer WHERE farmer_id = %s", (farmer_id,))
    farmer = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('profile.html', farmer=farmer) 

@app.route('/my_crops')
def my_crops():
    farmer_id = session.get('farmer_id') 
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            c.crop_id,
            c.crop_name,
            h.land_id,
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
    cur.close()
    conn.close()
    return render_template('my_crops.html', results=results)

@app.route('/yield_status')
def yield_status():
    farmer_id = session.get('farmer_id') 
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
    farmer_id = session.get('farmer_id')
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            i.inventory_id,
            i.inventory_name,
            mkt.market_name AS market_from_which_item_bought,
            m.purchase_date,
            mp.expiry_date,
            m.quantity_present,
            m.min_quantity,
            CASE 
                WHEN mp.expiry_date >= CURRENT_DATE THEN 'Valid'
                ELSE 'Expired'
            END AS validity
        FROM 
            maintains m
        JOIN 
            inventory i ON m.inventory_id = i.inventory_id
        JOIN 
            market mkt ON m.market_id = mkt.market_id
        JOIN 
            market_price mp ON m.market_id = mp.market_id AND m.inventory_id = mp.inventory_id
        WHERE 
            m.farmer_id = %s;
    """, (farmer_id,))
    inventory = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('my_inventory.html', data=inventory)

@app.route('/my_sales')
def my_sales():
    farmer_id = session.get('farmer_id')
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            s.sale_id,
            c.crop_id AS selling_crop_id,
            c.crop_name AS selling_crop_name,
            s.quantity_selling,
            s.amount_of_sale
        FROM 
            sale s
        JOIN 
            grows g ON s.grow_id = g.grow_id
        JOIN 
            crop c ON g.crop_id = c.crop_id
        WHERE 
            g.farmer_id = %s;
    """, (farmer_id,))
    sales = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('my_sales.html', data=sales)

@app.route('/my_land')
def my_land():
    farmer_id = session.get('farmer_id')
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

@app.route('/transaction_history')
def transaction_history():
    farmer_id = session.get('farmer_id')
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            p.purchase_id,
            p.sale_id,
            p.required_id, 
            f.farmer_id,
            f.farmer_name,
            b.buyer_id,
            b.buyer_name,
            p.purchase_date,
            p.amount_paid
        FROM 
            Purchase p
        JOIN 
            buyer_requirements br ON p.required_id = br.required_id
        JOIN 
            buyer b ON br.buyer_id = b.buyer_id
        JOIN 
            sale s ON p.sale_id = s.sale_id
        JOIN 
            grows g ON s.grow_id = g.grow_id 
        JOIN 
            farmer f ON g.farmer_id = f.farmer_id 
        WHERE 
            f.farmer_id = %s;
    """, (farmer_id,))
    transactions = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('transaction_history.html', data=transactions)

if __name__ == '__main__':
    app.run(debug=True, port = 5003) 