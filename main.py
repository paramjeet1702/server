import sqlite3
import re
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()
PORT = 3001

# Allow CORS and JSON body parsing so your React app can call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Open the SQLite database in read/write mode (mimicking sqlite3.OPEN_READWRITE)
try:
    db = sqlite3.connect('file:agents_data.db?mode=rw', uri=True, check_same_thread=False)
    logging.info("Connected to the SQLite database.")
except sqlite3.Error as e:
    logging.error("Error opening database: " + str(e))

# Set row_factory to return dictionary-like rows
db.row_factory = sqlite3.Row

# Create the Users table if it doesn't exist
try:
    db.execute(
        """CREATE TABLE IF NOT EXISTS Users (
            name TEXT PRIMARY KEY,
            email TEXT,
            password TEXT
        )"""
    )
    db.commit()
    logging.info("Users table is ready.")
    
    # Insert default user fsladmin if it doesn't already exist
    cursor = db.execute("SELECT * FROM Users WHERE name = ?", ("fsladmin",))
    row = cursor.fetchone()
    if not row:
        db.execute(
            "INSERT INTO Users (name, email, password) VALUES (?, ?, ?)",
            ("fsladmin", "fsladmin@firstsource.com", "fsladmin")
        )
        db.commit()
        logging.info("Default user fsladmin inserted.")
except sqlite3.Error as e:
    logging.error("Error creating Users table: " + str(e))


# Model for agent endpoints
class Agent(BaseModel):
    agent_name: str


# GET endpoint to fetch agents
@app.get("/api/agents")
def get_agents():
    try:
        cursor = db.execute("SELECT sr_number, agent_name, start_timestamp, stop_timestamp FROM agents")
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        return {"data": data}
    except sqlite3.Error as e:
        logging.error("Error querying agents: " + str(e))
        raise HTTPException(status_code=500, detail=str(e))


# GET endpoint to fetch unique agent names with their max sr_number
@app.get("/api/agents/max-sr")
def get_agents_max_sr():
    try:
        cursor = db.execute("SELECT agent_name, MAX(sr_number) AS max_sr_number FROM agents GROUP BY agent_name")
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]

        def getShortForm(name):
            # Split at capital letters, take the first letter of each part, and return the uppercase short form.
            parts = re.split('(?=[A-Z])', name)
            parts = [p for p in parts if p]  # filter out empty strings
            return ''.join([p[0] for p in parts]).upper()

        # Add short_name to each row
        for row in data:
            row["short_name"] = getShortForm(row["agent_name"])
        return {"data": data}
    except sqlite3.Error as e:
        logging.error("Error querying max sr_number for agents: " + str(e))
        raise HTTPException(status_code=500, detail=str(e))


# POST endpoint to add an agent
@app.post("/api/agents")
def add_agent(agent: Agent):
    if not agent.agent_name:
        raise HTTPException(status_code=400, detail="agent_name is required")
    try:
        cursor = db.execute(
            "INSERT INTO agents (agent_name, start_timestamp) VALUES (?, datetime('now'))",
            (agent.agent_name,)
        )
        db.commit()
        return {"data": {"sr_number": cursor.lastrowid, "agent_name": agent.agent_name}}
    except sqlite3.Error as e:
        logging.error("Error adding agent: " + str(e))
        raise HTTPException(status_code=500, detail=str(e))


# DELETE endpoint to remove an agent by name
@app.delete("/api/agents")
def delete_agent(agent: Agent):
    if not agent.agent_name:
        raise HTTPException(status_code=400, detail="agent_name is required")
    try:
        cursor = db.execute("DELETE FROM agents WHERE agent_name = ?", (agent.agent_name,))
        db.commit()
        return {"data": {"agent_name": agent.agent_name, "changes": cursor.rowcount}}
    except sqlite3.Error as e:
        logging.error("Error removing agent: " + str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Global exception logging similar to Node's process.on events
@app.exception_handler(Exception)
def global_exception_handler(request, exc):
    logging.error("Unhandled Exception: " + str(exc))
    return HTTPException(status_code=500, detail="Internal Server Error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=PORT, reload=True)
