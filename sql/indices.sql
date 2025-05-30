-- Indexes for foreign keys
CREATE INDEX idx_market_price_inventory_id ON market_price (inventory_id);
CREATE INDEX idx_market_price_market_id ON market_price (market_id);
CREATE INDEX idx_land_farmer_id ON land (farmer_id);
CREATE INDEX idx_grows_farmer_id ON grows (farmer_id);
CREATE INDEX idx_grows_crop_id ON grows (crop_id);
CREATE INDEX idx_harvest_land_id ON harvest (land_id);
CREATE INDEX idx_harvest_grow_id ON harvest (grow_id);
CREATE INDEX idx_maintains_farmer_id ON maintains (farmer_id);
CREATE INDEX idx_maintains_inventory_id ON maintains (inventory_id);
CREATE INDEX idx_maintains_market_id ON maintains (market_id);
CREATE INDEX idx_sale_grow_id ON sale (grow_id);
CREATE INDEX idx_purchase_sale_id ON purchase (sale_id);
CREATE INDEX idx_purchase_required_id ON purchase (required_id);
CREATE INDEX idx_buyer_requirements_buyer_id ON buyer_requirements (buyer_id);
CREATE INDEX idx_buyer_requirements_crop_id ON buyer_requirements (crop_id);

-- Indexes for frequently queried columns
CREATE INDEX idx_market_market_name ON market (market_name);
CREATE INDEX idx_farmer_farmer_name ON farmer (farmer_name);
CREATE INDEX idx_inventory_inventory_name ON inventory (inventory_name);
CREATE INDEX idx_crop_crop_name ON crop (crop_name);
CREATE INDEX idx_buyer_buyer_name ON buyer (buyer_name);
CREATE INDEX idx_maintains_purchase_date ON maintains (purchase_date);
CREATE INDEX idx_harvest_harvest_date ON harvest (harvest_date);

-- Multi-column indexes for better query performance
CREATE INDEX idx_market_price_market_inventory ON market_price (market_id, inventory_id);
CREATE INDEX idx_purchase_sale_date ON purchase (sale_id, purchase_date);

CREATE INDEX idx_grows_farmer_crops ON grows (farmer_id, crop_id);

EXPLAIN ANALYSE
SELECT f.farmer_name, c.crop_name
FROM farmer f
JOIN grows g ON f.farmer_id = g.farmer_id
JOIN crop c ON g.crop_id = c.crop_id
WHERE g.farmer_id = 100 AND g.crop_id = 50;

CREATE INDEX idx_harvest_land_date ON harvest (land_id, harvest_date);
DROP INDEX idx_harvest_land_date;

EXPLAIN ANALYSE
SELECT * 
FROM harvest 
WHERE land_id = 26 AND harvest_date BETWEEN '2024-01-01' AND '2025-12-31'
ORDER BY harvest_date;


CREATE INDEX idx_maintains_farmer_date ON maintains (farmer_id, purchase_date);
DROP INDEX idx_maintains_farmer_date;

EXPLAIN ANALYSE
SELECT * 
FROM maintains 
WHERE farmer_id = 1 AND purchase_date > '2024-01-01';










EXPLAIN ANALYSE
SELECT * FROM market WHERE market_name = 'Crop Market';
