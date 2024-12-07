import duckdb

db_path = 'auto_iot.duckdb'
conn = duckdb.connect(db_path, read_only=False)

conn.execute("DROP TABLE IF EXISTS sensor_data")
conn.execute("DROP TABLE IF EXISTS sensors")
conn.execute("DROP TABLE IF EXISTS locations")
conn.execute("DROP TABLE IF EXISTS companies")
conn.execute("DROP TABLE IF EXISTS admins")
conn.execute("DROP SEQUENCE IF EXISTS company_seq")
conn.execute("DROP SEQUENCE IF EXISTS location_seq")
conn.execute("DROP SEQUENCE IF EXISTS sensor_seq")

conn.execute("CREATE SEQUENCE company_seq START 1")
conn.execute("CREATE SEQUENCE location_seq START 1")
conn.execute("CREATE SEQUENCE sensor_seq START 1")

conn.execute("""
    CREATE TABLE companies (
        company_id INTEGER DEFAULT NEXTVAL('company_seq') PRIMARY KEY,
        company_name STRING NOT NULL,
        company_api_key STRING UNIQUE NOT NULL
    );
""")

conn.execute("""
    CREATE TABLE admins (
        username STRING PRIMARY KEY,
        password STRING NOT NULL,
    );
""")

conn.execute("""
    CREATE TABLE locations (
        location_id INTEGER DEFAULT NEXTVAL('location_seq') PRIMARY KEY,
        company_id INTEGER REFERENCES companies(company_id),
        location_name STRING NOT NULL,
        location_country STRING,
        location_city STRING,
        location_meta STRING
    );
""")

conn.execute("""
    CREATE TABLE sensors (
        sensor_id INTEGER DEFAULT NEXTVAL('sensor_seq') PRIMARY KEY,
        location_id INTEGER REFERENCES locations(location_id),
        sensor_name STRING NOT NULL,
        sensor_category STRING,
        sensor_meta STRING,
        sensor_api_key STRING UNIQUE NOT NULL
    );
""")

conn.execute("""
    CREATE TABLE sensor_data (
        sensor_id INTEGER REFERENCES sensors(sensor_id),
        json_data JSON,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")

# Insert a default admin
conn.execute("""
    INSERT INTO admins (username, password, company_id)
    VALUES ('admin', 'admin', NULL);
""")

conn.close()
print(f"Database created successfully at {db_path}")