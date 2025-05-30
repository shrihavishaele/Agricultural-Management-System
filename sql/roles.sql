--ROLES

CREATE ROLE farmer_role;
GRANT SELECT, INSERT, UPDATE ON farmer TO farmer_role;
GRANT SELECT, INSERT, UPDATE ON land TO farmer_role;
GRANT SELECT, INSERT, UPDATE ON grows TO farmer_role;
GRANT SELECT, INSERT, UPDATE ON harvest TO farmer_role;
GRANT SELECT, INSERT, UPDATE ON maintains TO farmer_role;

CREATE ROLE buyer_role;
GRANT SELECT, INSERT, UPDATE ON buyer TO buyer_role;
GRANT SELECT, INSERT, UPDATE ON buyer_requirements TO buyer_role;

CREATE ROLE admin_role;
GRANT SELECT, INSERT, UPDATE ON market TO admin_role;
GRANT SELECT, INSERT, UPDATE ON market_price TO admin_role;
GRANT SELECT, INSERT, UPDATE ON inventory TO admin_role;
GRANT SELECT ON maintains TO admin_role;
GRANT SELECT ON grows TO admin_role;
GRANT SELECT ON farmer TO admin_role;
GRANT SELECT ON land TO admin_role;
GRANT SELECT ON harvest TO admin_role;
GRANT SELECT ON buyer TO admin_role;
GRANT SELECT ON buyer_requirements TO admin_role;

select rolname from pg_roles;

SELECT 
    grantee AS role_name, 
    table_schema, 
    table_name, 
    privilege_type 
FROM information_schema.table_privileges 
WHERE table_schema = 'public'  -- Adjust schema name if needed
ORDER BY grantee, table_name;

SELECT 
    table_schema, 
    table_name, 
    privilege_type 
FROM information_schema.table_privileges 
WHERE grantee = 'farmer_role';

