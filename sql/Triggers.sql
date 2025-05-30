DROP FUNCTION IF EXISTS calculate_yield_before_insert CASCADE;


-- Drop existing triggers and functions
DROP TRIGGER IF EXISTS trigger_set_harvest_status_yield ON harvest;
DROP TRIGGER IF EXISTS trigger_update_grows_total_quantity ON harvest;
DROP FUNCTION IF EXISTS set_harvest_status_yield;
DROP FUNCTION IF EXISTS update_grows_total_quantity;

-- Create function for BEFORE INSERT/UPDATE to handle status and yield
CREATE OR REPLACE FUNCTION set_harvest_status_yield()
RETURNS TRIGGER AS $$
DECLARE
    ypa NUMERIC;
    old_yield NUMERIC;
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Check if harvest_date is on or before the current date
        IF NEW.harvest_date <= CURRENT_DATE THEN
            -- Get yield_per_acre from the crop table via grows
            SELECT yield_per_acre INTO ypa
            FROM crop
            WHERE crop_id = (SELECT crop_id FROM grows WHERE grow_id = NEW.grow_id);

            -- Calculate yield if yield_per_acre and area_used_in_acres are available
            IF ypa IS NOT NULL AND NEW.area_used_in_acres IS NOT NULL THEN
                NEW.yield := NEW.area_used_in_acres * ypa;
            END IF;

            -- Set status to 'C' (Completed)
            NEW.status := 'C';
        ELSE
            -- If harvest_date is in the future, set status to 'P' (Pending)
            NEW.status := 'P';
            -- Leave yield as is (could be NULL or a user-provided value)
        END IF;

        RETURN NEW;

    ELSIF TG_OP = 'UPDATE' THEN
        -- Store the old yield for adjustment
        old_yield := OLD.yield;

        -- Recalculate status and yield if harvest_date changes or status isn't already 'C'
        IF NEW.harvest_date != OLD.harvest_date AND NEW.status != 'C' THEN
            IF NEW.harvest_date <= CURRENT_DATE THEN
                -- Get yield_per_acre from the crop table via grows
                SELECT yield_per_acre INTO ypa
                FROM crop
                WHERE crop_id = (SELECT crop_id FROM grows WHERE grow_id = NEW.grow_id);

                -- Calculate yield if yield_per_acre and area_used_in_acres are available
                IF ypa IS NOT NULL AND NEW.area_used_in_acres IS NOT NULL THEN
                    NEW.yield := NEW.area_used_in_acres * ypa;
                END IF;

                -- Set status to 'C' (Completed)
                NEW.status := 'C';
            ELSE
                -- If harvest_date is in the future, set status to 'P' (Pending)
                NEW.status := 'P';
            END IF;
        END IF;

        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create function for AFTER INSERT/UPDATE to update total_quantity_present
CREATE OR REPLACE FUNCTION update_grows_total_quantity()
RETURNS TRIGGER AS $$
DECLARE
    old_yield NUMERIC;
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Update total_quantity_present in grows if yield is calculated or provided
        IF NEW.yield IS NOT NULL THEN
            UPDATE grows
            SET total_quantity_present = total_quantity_present + NEW.yield
            WHERE grow_id = NEW.grow_id;
        END IF;

        RETURN NEW;

    ELSIF TG_OP = 'UPDATE' THEN
        -- Store the old yield for adjustment
        old_yield := OLD.yield;

        -- Update total_quantity_present in grows if yield changes
        IF (OLD.yield IS DISTINCT FROM NEW.yield) THEN
            UPDATE grows
            SET total_quantity_present = total_quantity_present - COALESCE(old_yield, 0) + COALESCE(NEW.yield, 0)
            WHERE grow_id = NEW.grow_id;
        END IF;

        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create the triggers
CREATE TRIGGER trigger_set_harvest_status_yield
BEFORE INSERT OR UPDATE ON harvest
FOR EACH ROW
EXECUTE FUNCTION set_harvest_status_yield();

CREATE TRIGGER trigger_update_grows_total_quantity
AFTER INSERT OR UPDATE ON harvest
FOR EACH ROW
EXECUTE FUNCTION update_grows_total_quantity();


-- This trigger is used to check if the quantity_selling <= total_quantity_present 
CREATE OR REPLACE FUNCTION check_quantity_before_sale()
RETURNS TRIGGER AS $$
DECLARE
    available_qty NUMERIC;
BEGIN
    SELECT total_quantity_present INTO available_qty
    FROM grows
    WHERE grow_id = NEW.grow_id;

    IF NEW.quantity_selling > available_qty THEN
        RAISE EXCEPTION 'Selling quantity exceeds available quantity.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_quantity_before_sale
BEFORE INSERT ON sale
FOR EACH ROW
EXECUTE FUNCTION check_quantity_before_sale();



DROP FUNCTION IF EXISTS update_quantity_after_harvest CASCADE;


-- This trigger is used to check whether the land used is <= land_id.size 
CREATE OR REPLACE FUNCTION check_area_used_limit()
RETURNS TRIGGER AS $$
DECLARE
    land_sz NUMERIC;
BEGIN
    SELECT land_size INTO land_sz FROM land WHERE land_id = NEW.land_id;

    IF NEW.area_used_in_acres > land_sz THEN
        RAISE EXCEPTION 'Used area exceeds land size.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_area_used
BEFORE INSERT ON harvest
FOR EACH ROW
EXECUTE FUNCTION check_area_used_limit();

DROP FUNCTION IF EXISTS update_validity_in_maintains CASCADE;

-- This trigger is used to check whether an inventory is valid or not 
CREATE OR REPLACE FUNCTION update_validity_in_maintains()
RETURNS TRIGGER AS $$
DECLARE
    exp_date DATE;
BEGIN
    SELECT expiry_date INTO exp_date FROM market_price WHERE mp_id = NEW.mp_id;

    IF NEW.last_accessed::date >= exp_date THEN
        NEW.valid := 'N';
    ELSE
        NEW.valid := 'Y';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_validity
BEFORE INSERT OR UPDATE ON maintains
FOR EACH ROW
EXECUTE FUNCTION update_validity_in_maintains();


-- Recreate the function using the correct column name
CREATE OR REPLACE FUNCTION restore_quantity_after_sale_delete()
RETURNS TRIGGER AS $$
DECLARE
    is_purchased INT;
BEGIN
    -- Check if the sale exists in the purchase table
    SELECT COUNT(*) INTO is_purchased FROM purchase WHERE sale_id = OLD.sale_id;

    -- If not purchased, restore quantity
    IF is_purchased = 0 THEN
        UPDATE grows
        SET total_quantity_present = total_quantity_present + OLD.quantity_selling
        WHERE grow_id = OLD.grow_id;
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_restore_quantity_on_sale_delete
AFTER DELETE ON sale
FOR EACH ROW
EXECUTE FUNCTION restore_quantity_after_sale_delete();

-- Create a new function to reduce quantity after a sale is added
CREATE OR REPLACE FUNCTION reduce_quantity_after_sale_insert()
RETURNS TRIGGER AS $$
BEGIN
    -- Reduce the total_quantity_present by the quantity_selling
    UPDATE grows
    SET total_quantity_present = total_quantity_present - NEW.quantity_selling
    WHERE grow_id = NEW.grow_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger for sale insertion
CREATE TRIGGER trg_reduce_quantity_on_sale_insert
AFTER INSERT ON sale
FOR EACH ROW
EXECUTE FUNCTION reduce_quantity_after_sale_insert();

