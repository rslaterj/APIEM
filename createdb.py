import duckdb

db_path = 'iot.duckdb'
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
    CREATE TABLE admins (
        username String PRIMARY KEY,
        password String NOT NULL
    );
""")

conn.execute("""
    CREATE TABLE companies (
        company_id INTEGER DEFAULT NEXTVAL('company_seq') PRIMARY KEY,
        company_name String NOT NULL,
        company_api_key String UNIQUE NOT NULL
    );
""")

conn.execute("""
    CREATE TABLE locations (
        location_id INTEGER DEFAULT NEXTVAL('location_seq') PRIMARY KEY,
        company_id INTEGER REFERENCES companies(company_id),
        location_name String NOT NULL,
        location_country String,
        location_city String,
        location_meta String
    );
""")

conn.execute("""
    CREATE TABLE sensors (
        sensor_id INTEGER DEFAULT NEXTVAL('sensor_seq') PRIMARY KEY,
        location_id INTEGER REFERENCES locations(location_id),
        sensor_name String NOT NULL,
        sensor_category String,
        sensor_meta String,
        sensor_api_key String UNIQUE NOT NULL
    );
""")

conn.execute("""
    CREATE TABLE sensor_data (
        sensor_id INTEGER REFERENCES sensors(sensor_id),
        json_data JSON,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")

#Crea un Admin predeterminado
conn.execute("""
    INSERT INTO admins (username, password) 
    VALUES ('admin', 'admin');
""")

conn.close()
print(f"Database created successfully at {db_path}")

