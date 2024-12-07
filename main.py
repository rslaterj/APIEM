import uuid
import duckdb
import secrets
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel
from typing import List, Dict, Optional

app = FastAPI()
#db_path = 'iot.duckdb'
db_path = 'auto_iot.duckdb'
conn = duckdb.connect(db_path)
tokens = {}

class Location(BaseModel):
    company_id: int
    location_name: str
    location_country: str
    location_city: str
    location_meta: Optional[str] = None

class Sensor(BaseModel):
    location_id: int
    sensor_name: str
    sensor_category: str
    sensor_meta: Optional[str] = None

class SensorData(BaseModel):
    api_key: str
    json_data: List[Dict]

class Company(BaseModel):
    #company_id: int
    company_name: str
    #company_api_key: str

class LoginRequest(BaseModel):
    username: str
    password: str

def generate_api_key():
    return str(uuid.uuid4())

#----------------------------------------------------------#
#                   VALIDATION FUNCTIONS                   #
#----------------------------------------------------------#

def authenticate_admin(credentials: HTTPBasicCredentials):
    result = conn.execute("SELECT password FROM admins WHERE username = ?", (credentials.username,)).fetchone()
    if not result or result[0] != credentials.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_hex(16)
    tokens[token] = credentials.username
    return token

def get_current_user(token: str):
    if token not in tokens:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return tokens[token]

def validate_company_api_key(company_api_key: str):
    result = conn.execute("SELECT 1 FROM companies WHERE company_api_key = ?", (company_api_key,)).fetchone()
    if not result:
        raise HTTPException(status_code=403, detail="Invalid company API key")
    return True

def validate_sensor_api_key(sensor_api_key: str):
    result = conn.execute("SELECT sensor_id FROM sensors WHERE sensor_api_key = ?", (sensor_api_key,)).fetchone()
    if not result:
        raise HTTPException(status_code=403, detail="Invalid sensor API key")
    return result[0]  # Return the sensor_id associated with the API key


#API AUTH.
@app.post("/api/authenticate")
async def login(request: LoginRequest):
    if conn.execute("SELECT 1 FROM admins WHERE username = ? AND password = ?", (request.username, request.password)).fetchone():
        token = secrets.token_hex(16)
        tokens[token] = request.username
        return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid credentials")

#----------------------------------------------------------#
#                       COMPANY REST                       #
#           (get_all, get_one, add_one, delete_one)        #
#----------------------------------------------------------#

@app.post("/api/companies")
@app.post("/api/companies")
async def add_company(company: Company, token: str = Header(...)):
    get_current_user(token)
    company_api_key = generate_api_key()
    conn.execute("""
        INSERT INTO companies (company_name, company_api_key)
        VALUES (?, ?)
    """, (company.company_name, company_api_key))
    new_company_id = conn.execute("SELECT MAX(company_id) FROM companies").fetchone()[0]
    return {"message": "Company added successfully", "company_id": new_company_id, "company_api_key": company_api_key}

@app.get("/api/companies")
async def get_companies(token: str, company_api_key: str):
    get_current_user(token)
    validate_company_api_key(company_api_key)
    companies = conn.execute("SELECT * FROM companies").fetchall()
    return [{"company_id": c[0],
             "company_name": c[1],
             "company_api_key": c[2]}
            for c in companies]

@app.get("/api/companies/{company_id}")
async def get_company(company_id: int, token: str = Header(...), company_api_key: str = Header(...)):
    get_current_user(token)
    validate_company_api_key(company_api_key)
    company = conn.execute("SELECT * FROM companies WHERE company_id = ?", (company_id,)).fetchone()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"company_id": company[0],
            "company_name": company[1],
            "company_api_key": company[2]}

@app.put("/api/companies/{company_id}")
async def update_company(company_id: int, company: Company, token: str, company_api_key: str):
    get_current_user(token)
    validate_company_api_key(company_api_key)
    conn.execute("""
        UPDATE companies SET company_name = ?, company_api_key = ? WHERE company_id = ?
    """, (company.company_name, company.company_api_key, company_id))
    return {"message": "Company updated successfully"}

@app.delete("/api/companies/{company_id}")
async def delete_company(company_id: int, token: str, company_api_key: str):
    get_current_user(token)
    validate_company_api_key(company_api_key)
    conn.execute("DELETE FROM companies WHERE company_id = ?", (company_id,))
    return {"message": "Company deleted successfully"}

#----------------------------------------------------------#
#                       LOCATION REST                      #
#           (get_all, get_one, add_one, delete_one)        #
#----------------------------------------------------------#

@app.post("/api/locations")
async def add_location(location: Location, token: str = Header(...), company_api_key: str = Header(...)):
    get_current_user(token)
    validate_company_api_key(company_api_key)
    conn.execute("""
        INSERT INTO locations (company_id, location_name, location_country, location_city, location_meta)
        VALUES (?, ?, ?, ?, ?)
    """, (location.company_id, location.location_name, location.location_country, location.location_city, location.location_meta))
    new_location_id = conn.execute("SELECT MAX(location_id) FROM locations").fetchone()[0]
    return {"message": "Location added successfully", "location_id": new_location_id}


#Make this only return the locations from the company api key
@app.get("/api/locations")
async def get_locations(token: str = Header(...), company_api_key: str = Header(...)):
    get_current_user(token)
    validate_company_api_key(company_api_key)
    locations = conn.execute("SELECT * FROM locations").fetchall()
    return [{"location_id": loc[0],
             "company_id": loc[1],
             "location_name": loc[2],
             "location_country": loc[3],
             "location_city": loc[4],
             "location_meta": loc[5]}
            for loc in locations]

@app.get("/api/locations/{location_id}")
async def get_location(location_id: int, token: str = Header(...), company_api_key: str = Header(...)):
    get_current_user(token)
    validate_company_api_key(company_api_key)
    location = conn.execute("""
        SELECT l.location_id, l.company_id, l.location_name, l.location_country, l.location_city, l.location_meta
        FROM locations l
        JOIN companies c ON l.company_id = c.company_id
        WHERE l.location_id = ? AND c.company_api_key = ?
    """, (location_id, company_api_key)).fetchone()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found or does not belong to the company")
    return {"location_id": location[0],
            "company_id": location[1],
            "location_name": location[2],
            "location_country": location[3],
            "location_city": location[4],
            "location_meta": location[5]}

@app.put("/api/locations/{location_id}")
async def update_location(location_id: int, location: Location, token: str, company_api_key: str):
    get_current_user(token)
    validate_company_api_key(company_api_key)
    conn.execute("""
        UPDATE locations SET company_id = ?, location_name = ?, location_country = ?, location_city = ?, location_meta = ?
        WHERE location_id = ?
    """, (location.company_id, location.location_name, location.location_country, location.location_city, location.location_meta, location_id))
    return {"message": "Location updated successfully"}

@app.delete("/api/locations/{location_id}")
async def delete_location(location_id: int, token: str, company_api_key: str):
    get_current_user(token)
    validate_company_api_key(company_api_key)
    conn.execute("DELETE FROM locations WHERE location_id = ?", (location_id,))
    return {"message": "Location deleted successfully"}

#----------------------------------------------------------#
#                       SENSOR REST                        #
#           (get_all, get_one, add_one, delete_one)        #
#----------------------------------------------------------#

@app.post("/api/sensors")
async def add_sensor(sensor: Sensor, token: str = Header(...), company_api_key: str = Header(...)):
    get_current_user(token)
    validate_company_api_key(company_api_key)
    sensor_api_key = generate_api_key()
    conn.execute("""
        INSERT INTO sensors (location_id, sensor_name, sensor_category, sensor_meta, sensor_api_key)
        VALUES (?, ?, ?, ?, ?)
    """, (sensor.location_id, sensor.sensor_name, sensor.sensor_category, sensor.sensor_meta, sensor_api_key))
    new_sensor_id = conn.execute("SELECT MAX(sensor_id) FROM sensors").fetchone()[0]
    return {"message": "Sensor added successfully", "sensor_id": new_sensor_id, "sensor_api_key": sensor_api_key}

@app.get("/api/sensors") #ALL SENSORS
async def get_sensors(token: str = Header(...), company_api_key: str = Header(...)):
    get_current_user(token)
    validate_company_api_key(company_api_key)
    sensors = conn.execute("""
        SELECT s.sensor_id, s.location_id, s.sensor_name, s.sensor_category, s.sensor_meta, s.sensor_api_key
        FROM sensors s
        JOIN locations l ON s.location_id = l.location_id
        JOIN companies c ON l.company_id = c.company_id
        WHERE c.company_api_key = ?
    """, (company_api_key,)).fetchall()
    return [{"sensor_id": sens[0],
             "location_id": sens[1],
             "sensor_name": sens[2],
             "sensor_category": sens[3],
             "sensor_meta": sens[4],
             "sensor_api_key": sens[5]}
            for sens in sensors]

@app.get("/api/locations/{location_id}/sensors") #LOCATION SENSORS
async def get_sensors_by_location(location_id: int, token: str = Header(...), company_api_key: str = Header(...)):
    get_current_user(token)
    validate_company_api_key(company_api_key)
    sensors = conn.execute("""
        SELECT s.sensor_id, s.location_id, s.sensor_name, s.sensor_category, s.sensor_meta, s.sensor_api_key
        FROM sensors s
        JOIN locations l ON s.location_id = l.location_id
        JOIN companies c ON l.company_id = c.company_id
        WHERE s.location_id = ? AND c.company_api_key = ?
    """, (location_id, company_api_key)).fetchall()
    return [{"sensor_id": sens[0],
             "location_id": sens[1],
             "sensor_name": sens[2],
             "sensor_category": sens[3],
             "sensor_meta": sens[4],
             "sensor_api_key": sens[5]}
            for sens in sensors]

@app.get("/api/sensors/{sensor_id}")
async def get_sensor(sensor_id: int, token: str = Header(...), company_api_key: str = Header(...)):
    get_current_user(token)
    validate_company_api_key(company_api_key)
    sensor = conn.execute("""
        SELECT s.sensor_id, s.location_id, s.sensor_name, s.sensor_category, s.sensor_meta, s.sensor_api_key
        FROM sensors s
        JOIN locations l ON s.location_id = l.location_id
        JOIN companies c ON l.company_id = c.company_id
        WHERE s.sensor_id = ? AND c.company_api_key = ?
    """, (sensor_id, company_api_key)).fetchone()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found or does not belong to the company")
    return {"sensor_id": sensor[0],
            "location_id": sensor[1],
            "sensor_name": sensor[2],
            "sensor_category": sensor[3],
            "sensor_meta": sensor[4],
            "sensor_api_key": sensor[5]}

@app.put("/api/sensors/{sensor_id}")
async def update_sensor(sensor_id: int, sensor: Sensor, token: str, company_api_key: str):
    get_current_user(token)
    validate_company_api_key(company_api_key)
    conn.execute("""
        UPDATE sensors SET location_id = ?, sensor_name = ?, sensor_category = ?, sensor_meta = ? 
        WHERE sensor_id = ?
    """, (sensor.location_id, sensor.sensor_name, sensor.sensor_category, sensor.sensor_meta, sensor_id))
    return {"message": "Sensor updated successfully"}

@app.delete("/api/sensors/{sensor_id}")
async def delete_sensor(sensor_id: int, token: str, company_api_key: str):
    get_current_user(token)
    validate_company_api_key(company_api_key)
    conn.execute("DELETE FROM sensors WHERE sensor_id = ?", (sensor_id,))
    return {"message": "Sensor deleted successfully"}

#----------------------------------------------------------#
#                      SENSOR-DATA REST                    #
#           (get_all, get_one, add_one, delete_one)        #
#----------------------------------------------------------#

@app.post("/api/v1/sensor_data", status_code=201)
async def add_sensor_data(data: SensorData, request: Request):
    sensor_api_key = request.headers.get("Authorization")
    if not sensor_api_key:
        raise HTTPException(status_code=401, detail="Missing sensor API key")
    sensor_id = validate_sensor_api_key(sensor_api_key)
    conn.execute("""
        INSERT INTO sensor_data (sensor_id, json_data)
        VALUES (?, ?)
    """, (sensor_id, str(data.json_data)))
    return {"message": "Sensor data added successfully"}

#add data v1
#@app.post("/api/sensor_data", status_code=201)
#async def add_sensor_data(data: SensorData, token: str):
#    get_current_user(token)
#    sensor_id = validate_sensor_api_key(data.api_key)
#    conn.execute("""
#        INSERT INTO sensor_data (sensor_id, json_data)
#        VALUES (?, ?)
#   """, (sensor_id, str(data.json_data)))
#    return {"message": "Sensor data added successfully"}
#REVISAR TABLAS!!

@app.get("/api/sensors/{sensor_id}/data")
async def get_sensor_data(sensor_id: int, token: str, company_api_key: str):
    get_current_user(token)
    validate_company_api_key(company_api_key)
    data = conn.execute("SELECT json_data, timestamp FROM sensor_data WHERE sensor_id = ?", (sensor_id,)).fetchall()
    return [{"json_data": d[0], "timestamp": d[1]} for d in data]

@app.put("/api/sensors/{sensor_id}/data")
async def update_sensor_data(sensor_id: int, data: SensorData, token: str):
    get_current_user(token)
    sensor_id_from_key = validate_sensor_api_key(data.api_key)
    if sensor_id_from_key != sensor_id:
        raise HTTPException(status_code=403, detail="API key does not match the sensor ID")
    conn.execute("""
        UPDATE sensor_data SET json_data = ? WHERE sensor_id = ?
    """, (str(data.json_data), sensor_id))
    return {"message": "Sensor data updated successfully"}

@app.delete("/api/sensors/{sensor_id}/data")
async def delete_sensor_data(sensor_id: int, api_key: str, token: str):
    get_current_user(token)
    sensor_id_from_key = validate_sensor_api_key(api_key)
    if sensor_id_from_key != sensor_id:
        raise HTTPException(status_code=403, detail="API key does not match the sensor ID")
    conn.execute("DELETE FROM sensor_data WHERE sensor_id = ?", (sensor_id,))
    return {"message": "Sensor data deleted successfully"}