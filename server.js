const express = require("express");
const sqlite3 = require("sqlite3").verbose();
const cors = require("cors");

const app = express();
const PORT = 3001;

// Allow CORS and JSON body parsing so your React app can call this API
app.use(cors());
app.use(express.json());

// Open the SQLite database in read/write mode
const db = new sqlite3.Database("agents_data.db", sqlite3.OPEN_READWRITE, (err) => {
  if (err) {
    console.error("Error opening database:", err.message);
  } else {
    console.log("Connected to the SQLite database.");
  }
});

// Create the Users table if it doesn't exist
db.run(
  `CREATE TABLE IF NOT EXISTS Users (
    name TEXT PRIMARY KEY,
    email TEXT,
    password TEXT
  )`,
  (err) => {
    if (err) {
      console.error("Error creating Users table:", err.message);
    } else {
      console.log("Users table is ready.");
      // Insert default user fsladmin if it doesn't already exist
      db.get("SELECT * FROM Users WHERE name = ?", ["fsladmin"], (err, row) => {
        if (err) {
          console.error("Error querying Users table:", err.message);
        } else if (!row) {
          db.run(
            "INSERT INTO Users (name, email, password) VALUES (?, ?, ?)",
            ["fsladmin", "fsladmin@firstsource.com", "fsladmin"],
            function (err) {
              if (err) {
                console.error("Error inserting default user:", err.message);
              } else {
                console.log("Default user fsladmin inserted.");
              }
            }
          );
        }
      });
    }
  }
);

// GET endpoint to fetch agents
app.get("/api/agents", (req, res) => {
  const sql = `SELECT sr_number, agent_name, start_timestamp, stop_timestamp FROM agents`;
  db.all(sql, [], (err, rows) => {
    if (err) {
      console.error("Error querying agents:", err.message);
      res.status(500).json({ error: err.message });
      return;
    }
    res.json({ data: rows });
  });
});

// GET endpoint to fetch unique agent names with their max sr_number
app.get("/api/agents/max-sr", (req, res) => {
  const sql = `SELECT agent_name, MAX(sr_number) AS max_sr_number FROM agents GROUP BY agent_name`;
  
  db.all(sql, [], (err, rows) => {
    if (err) {
      console.error("Error querying max sr_number for agents:", err.message);
      res.status(500).json({ error: err.message });
      return;
    }

    // Function to generate short form
    const getShortForm = (name) => {
      return name
        .split(/(?=[A-Z])/) // Split at capital letters
        .map(word => word[0]) // Take first letter of each part
        .join('')
        .toUpperCase(); // Ensure uppercase
    };

    // Add short_name to each row
    const formattedRows = rows.map(row => ({
      ...row,
      short_name: getShortForm(row.agent_name)
    }));

    res.json({ data: formattedRows });
  });
});


// POST endpoint to add an agent
app.post("/api/agents", (req, res) => {
  const { agent_name } = req.body;
  if (!agent_name) {
    return res.status(400).json({ error: "agent_name is required" });
  }
  // Insert a new agent. (If your table has an auto-increment sr_number, it will be generated automatically.)
  const sql = `INSERT INTO agents (agent_name, start_timestamp) VALUES (?, datetime('now'))`;
  db.run(sql, [agent_name], function (err) {
    if (err) {
      console.error("Error adding agent:", err.message);
      return res.status(500).json({ error: err.message });
    }
    // Return the newly created agent (including the generated sr_number)
    res.json({ data: { sr_number: this.lastID, agent_name } });
  });
});

// DELETE endpoint to remove an agent by name
app.delete("/api/agents", (req, res) => {
  const { agent_name } = req.body;
  if (!agent_name) {
    return res.status(400).json({ error: "agent_name is required" });
  }
  const sql = `DELETE FROM agents WHERE agent_name = ?`;
  db.run(sql, [agent_name], function (err) {
    if (err) {
      console.error("Error removing agent:", err.message);
      return res.status(500).json({ error: err.message });
    }
    res.json({ data: { agent_name, changes: this.changes } });
  });
});




process.on("uncaughtException", (err) => {
  console.error("Unhandled Exception:", err);
});

process.on("unhandledRejection", (reason, promise) => {
  console.error("Unhandled Rejection:", reason);
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});