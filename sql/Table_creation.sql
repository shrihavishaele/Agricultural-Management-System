CREATE TABLE inventory (
    inventory_id SERIAL PRIMARY KEY,
    inventory_name VARCHAR(50) NOT NULL,
    category VARCHAR(50),
    avg_price_per_unit INTEGER,
	unit CHAR 
);

CREATE TABLE market (
    market_id SERIAL PRIMARY KEY,
    market_name VARCHAR(50) NOT NULL,
    location VARCHAR(50),
    rating_out_of_10 INTEGER
);

CREATE TABLE market_price (
    mp_id SERIAL PRIMARY KEY,
    inventory_id INTEGER REFERENCES inventory(inventory_id),
    market_id INTEGER REFERENCES market(market_id),
    price_per_unit INTEGER,
    expiry_date DATE
);

CREATE TABLE farmer (
    farmer_id SERIAL PRIMARY KEY,
    farmer_name VARCHAR(50) NOT NULL,
    email_id VARCHAR(50),
	password VARCHAR(50),
    address VARCHAR(50),
    contact_no VARCHAR(15) NOT NULL
);

CREATE TABLE land (
    land_id SERIAL PRIMARY KEY,
    land_size NUMERIC(5,2),
    soil_type VARCHAR(50),
    location VARCHAR(50),
    farmer_id INTEGER REFERENCES farmer(farmer_id),
    ownership VARCHAR(50)
);

CREATE TABLE crop (
    crop_id SERIAL PRIMARY KEY,
    crop_name VARCHAR(20),
    crop_type VARCHAR(20),
    yield_per_acre NUMERIC(5,2),
	unit CHAR,
    market_price_per_unit INTEGER
);

CREATE TABLE buyer (
    buyer_id SERIAL PRIMARY KEY,
    buyer_name VARCHAR(50),
    email_id VARCHAR(50),
    address VARCHAR(50),
    contact_no INTEGER
);

CREATE TABLE buyer_requirements (
    required_id SERIAL PRIMARY KEY,
    buyer_id INTEGER REFERENCES buyer(buyer_id),
    crop_id INTEGER REFERENCES crop(crop_id),
    quantity NUMERIC(5,2),
	unit CHAR,
    min_afford INTEGER,
    max_afford INTEGER
);

CREATE TABLE grows (
    grow_id SERIAL PRIMARY KEY,
    farmer_id INTEGER REFERENCES farmer(farmer_id),
    crop_id INTEGER REFERENCES crop(crop_id),
	total_quantity_present NUMERIC 
);

CREATE TABLE harvest (
    harvest_id SERIAL PRIMARY KEY,
    land_id INTEGER REFERENCES land(land_id),
    grow_id INTEGER REFERENCES grows(grow_id),
    sowing_date DATE,
    harvest_date DATE,
    area_used_in_acres NUMERIC(5,2),
    yield NUMERIC(7,2),
    unit CHAR,
    status CHAR 
);

CREATE TABLE maintains (
    maintains_id SERIAL PRIMARY KEY,
    farmer_id INTEGER REFERENCES farmer(farmer_id),
    inventory_id INTEGER REFERENCES inventory(inventory_id),
    market_id INTEGER REFERENCES market(market_id),
    purchase_date DATE,
    quantity_present NUMERIC,
    min_quantity NUMERIC,
	unit CHAR,
    valid CHAR,
    last_accessed DATE
);

CREATE TABLE sale (
    sale_id SERIAL PRIMARY KEY,
    grow_id INTEGER REFERENCES grows(grow_id),
    quantity_selling INTEGER,
	unit CHAR, 
    amount_of_sale INTEGER
);

CREATE TABLE purchase (
    purchase_id SERIAL PRIMARY KEY,
    sale_id INTEGER REFERENCES sale(sale_id),
    required_id INTEGER REFERENCES buyer_requirements(required_id),
    purchase_date TIME WITHOUT TIME ZONE,
    amount_paid INTEGER
);

