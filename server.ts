import express, { Request, Response, NextFunction } from "express";
import { createServer as createViteServer } from "vite";
import path from "path";
import { fileURLToPath } from "url";
import cors from "cors";
import dotenv from "dotenv";
import Database from "better-sqlite3";
import axios from "axios";
import asyncHandler from "express-async-handler";
import { createRequire } from "module";
const require = createRequire(import.meta.url);
const { GarminConnect } = require("garmin-connect");

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// REQ-B12: Initialize SQLite Database
const db = new Database("atlas.db");

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );
  CREATE TABLE IF NOT EXISTS tokens (
    user_id TEXT PRIMARY KEY,
    email TEXT,
    password TEXT,
    garmin_session TEXT,
    wger_api_key TEXT,
    hevy_username TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
  );
  CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    source TEXT,
    external_id TEXT,
    name TEXT,
    description TEXT,
    date DATETIME,
    duration INTEGER,
    calories INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id),
    UNIQUE(user_id, source, external_id)
  );
  CREATE TABLE IF NOT EXISTS biometrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    date TEXT,
    data TEXT,
    source TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
  );
`);

// Ensure default user exists
db.prepare("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)").run("default_user", "Atleta ATLAS");

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(cors({ origin: process.env.FRONTEND_URL || "*" }));
  app.use(express.json());

  // REQ-B15: Health Check
  app.get("/health", (req, res) => res.json({ status: "ok" }));

  // REQ-B16: CSP Headers (to address report-only violations if possible)
  app.use((req, res, next) => {
    res.setHeader("Content-Security-Policy-Report-Only", "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: https:; font-src 'self' data: https: https://fonts.gstatic.com; connect-src 'self' wss: https://api.groq.com https://api.openai.com https://api.anthropic.com;");
    next();
  });

  // Garmin Login (Private API approach like AI_Fitness repo)
  app.post("/auth/garmin/login", asyncHandler(async (req, res) => {
    const { email, password, userId } = req.body;
    if (!email || !password || !userId) {
      res.status(400).json({ error: "Email, password and userId are required" });
      return;
    }

    try {
      console.log(`Attempting Garmin login for user: ${email}`);
      const client = new GarminConnect();
      await client.login(email, password);
      const session = client.session;
      
      console.log("Garmin login successful, storing session.");
      // Store credentials and session
      db.prepare("INSERT OR REPLACE INTO tokens (user_id, email, password, garmin_session) VALUES (?, ?, ?, ?)")
        .run(userId, email, password, JSON.stringify(session));

      res.json({ success: true });
    } catch (error: any) {
      console.error("Garmin Login Error Detail:", error);
      res.status(401).json({ 
        error: "Invalid credentials or MFA required",
        details: error.message 
      });
    }
  }));

  // REQ-B04: Auth Status
  app.get("/auth/status", (req, res) => {
    const userId = req.headers["x-user-id"] as string || "default_user";
    const token = db.prepare("SELECT * FROM tokens WHERE user_id = ?").get(userId) as any;
    res.json({ authenticated: !!token });
  });

  // REQ-B05: Disconnect
  app.post("/auth/disconnect", (req, res) => {
    const userId = req.headers["x-user-id"] as string || "default_user";
    db.prepare("DELETE FROM tokens WHERE user_id = ?").run(userId);
    res.json({ success: true });
  });

  // REQ-B20: Update Service Credentials (Wger, Hevy)
  app.post("/api/settings/services", asyncHandler(async (req, res) => {
    const userId = req.headers["x-user-id"] as string || "default_user";
    const { wger_api_key, hevy_username } = req.body;
    
    db.prepare("INSERT INTO tokens (user_id, wger_api_key, hevy_username) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET wger_api_key=excluded.wger_api_key, hevy_username=excluded.hevy_username")
      .run(userId, wger_api_key || null, hevy_username || null);
    
    res.json({ success: true });
  }));

  // GET Service Credentials
  app.get("/api/settings/services", asyncHandler(async (req, res) => {
    const userId = req.headers["x-user-id"] as string || "default_user";
    const credentials = db.prepare("SELECT wger_api_key, hevy_username FROM tokens WHERE user_id = ?").get(userId) as any;
    
    res.json({
      wger_api_key: credentials?.wger_api_key || "",
      hevy_username: credentials?.hevy_username || ""
    });
  }));

  // REQ-B21: Sync Garmin Activities
  app.post("/api/sync/garmin", asyncHandler(async (req, res) => {
    const userId = req.headers["x-user-id"] as string || "default_user";
    const credentials = db.prepare("SELECT * FROM tokens WHERE user_id = ?").get(userId) as any;
    
    if (!credentials || !credentials.email || !credentials.password) {
      res.status(400).json({ error: "Garmin credentials not found" });
      return;
    }

    try {
      const client = new GarminConnect();
      await client.login(credentials.email, credentials.password);
      const activities = await client.getActivities(0, 10); // Get last 10 activities
      
      for (const activity of activities) {
        db.prepare(`
          INSERT INTO workouts (user_id, source, external_id, name, description, date, duration, calories)
          VALUES (?, 'garmin', ?, ?, ?, ?, ?, ?)
          ON CONFLICT(user_id, source, external_id) DO UPDATE SET
            name=excluded.name, description=excluded.description, date=excluded.date, duration=excluded.duration, calories=excluded.calories
        `).run(
          userId,
          activity.activityId.toString(),
          activity.activityName,
          activity.description || "",
          activity.startTimeLocal,
          Math.round(activity.duration),
          Math.round(activity.calories)
        );
      }
      
      res.json({ success: true, count: activities.length });
    } catch (error: any) {
      console.error("Garmin Sync Error:", error.message);
      res.status(500).json({ error: "Failed to sync Garmin activities" });
    }
  }));

  // REQ-B22: Sync Wger Data
  app.post("/api/sync/wger", asyncHandler(async (req, res) => {
    const userId = req.headers["x-user-id"] as string || "default_user";
    const credentials = db.prepare("SELECT * FROM tokens WHERE user_id = ?").get(userId) as any;
    
    if (!credentials || !credentials.wger_api_key) {
      res.status(400).json({ error: "Wger API key not found" });
      return;
    }

    try {
      const response = await axios.get("https://wger.de/api/v2/workout/", {
        headers: { "Authorization": `Token ${credentials.wger_api_key}` }
      });
      
      const workouts = response.data.results;
      for (const workout of workouts) {
        db.prepare(`
          INSERT INTO workouts (user_id, source, external_id, name, description, date)
          VALUES (?, 'wger', ?, ?, ?, ?)
          ON CONFLICT(user_id, source, external_id) DO UPDATE SET
            name=excluded.name, description=excluded.description, date=excluded.date
        `).run(
          userId,
          workout.id.toString(),
          workout.comment || "Workout",
          workout.description || "",
          workout.creation_date
        );
      }
      
      res.json({ success: true, count: workouts.length });
    } catch (error: any) {
      console.error("Wger Sync Error:", error.message);
      res.status(500).json({ error: "Failed to sync Wger data" });
    }
  }));

  // REQ-B23: Sync Hevy Data (Public Profile approach)
  app.post("/api/sync/hevy", asyncHandler(async (req, res) => {
    const userId = req.headers["x-user-id"] as string || "default_user";
    const credentials = db.prepare("SELECT * FROM tokens WHERE user_id = ?").get(userId) as any;
    
    if (!credentials || !credentials.hevy_username) {
      res.status(400).json({ error: "Hevy username not found" });
      return;
    }

    try {
      // Mocking Hevy sync by adding a random workout
      const mockWorkout = {
        external_id: "hevy_" + Date.now(),
        name: "Hevy Strength Session",
        description: "Push/Pull/Legs - Intensity High",
        date: new Date().toISOString(),
        duration: 3600,
        calories: 450
      };

      db.prepare(`
        INSERT INTO workouts (user_id, source, external_id, name, description, date, duration, calories)
        VALUES (?, 'hevy', ?, ?, ?, ?, ?, ?)
      `).run(
        userId,
        mockWorkout.external_id,
        mockWorkout.name,
        mockWorkout.description,
        mockWorkout.date,
        mockWorkout.duration,
        mockWorkout.calories
      );
      
      res.json({ success: true, message: `Synced workouts for ${credentials.hevy_username} (Mocked)` });
    } catch (error: any) {
      console.error("Hevy Sync Error:", error.message);
      res.status(500).json({ error: "Failed to sync Hevy data" });
    }
  }));

  // GET Workouts
  app.get("/api/workouts", asyncHandler(async (req, res) => {
    const userId = req.headers["x-user-id"] as string || "default_user";
    const workouts = db.prepare("SELECT * FROM workouts WHERE user_id = ? ORDER BY date DESC LIMIT 20").all(userId);
    res.json(workouts);
  }));

  // REQ-B06 & REQ-B07: Biometrics API
  app.get("/api/biometrics", asyncHandler(async (req, res) => {
    const userId = req.headers["x-user-id"] as string || "default_user";
    const dateStr = (req.query.date as string) || new Date().toISOString().split("T")[0];

    // Check Cache (REQ-B06)
    const cached = db.prepare("SELECT * FROM biometrics WHERE user_id = ? AND date = ? AND timestamp > datetime('now', '-5 minutes')").get(userId, dateStr) as any;
    if (cached) {
      res.json({ ...JSON.parse(cached.data), source: "cache" });
      return;
    }

    const credentials = db.prepare("SELECT * FROM tokens WHERE user_id = ?").get(userId) as any;
    
    // REQ-B08: Fallback to Demo Data
    if (!credentials) {
      const demoData = generateDemoData();
      res.json({ ...demoData, source: "demo" });
      return;
    }

    try {
      const client = new GarminConnect();
      
      if (credentials.garmin_session) {
        client.session = JSON.parse(credentials.garmin_session);
      } else {
        await client.login(credentials.email, credentials.password);
        // Update session in DB
        db.prepare("UPDATE tokens SET garmin_session = ? WHERE user_id = ?")
          .run(JSON.stringify(client.session), userId);
      }
      
      const date = new Date(dateStr);
      
      // Fetch data in parallel (REQ-B07)
      const [heartRateData, sleepData, stressData, stepsData] = await Promise.all([
        client.getHeartRate(date),
        client.getSleepData(date),
        client.getStressData(date),
        client.getSteps(date)
      ]);

      const biometrics = {
        heartRate: heartRateData?.lastSevenDaysAvgRestingHeartRate || 70,
        hrv: heartRateData?.heartRateValues?.length > 0 ? 50 : 0, // Simplified HRV
        spo2: 98, // SpO2 often requires specific endpoint
        stress: stressData?.avgStressLevel || 30,
        steps: stepsData || 0,
        sleep: sleepData?.dailySleepDTO?.sleepTimeSeconds ? (sleepData.dailySleepDTO.sleepTimeSeconds / 3600) : 0,
        calories: 2000,
        respiration: 14
      };

      const enriched = enrichBiometrics(biometrics);

      db.prepare("INSERT INTO biometrics (user_id, date, data, source) VALUES (?, ?, ?, ?)")
        .run(userId, dateStr, JSON.stringify(enriched), "garmin_api");

      res.json({ ...enriched, source: "garmin_api" });
    } catch (error: any) {
      console.error("Garmin Fetch Error:", error.message);
      const demoData = generateDemoData();
      res.json({ ...demoData, source: "demo", error: "Failed to fetch real data" });
    }
  }));

  function generateDemoData() {
    return {
      heartRate: 68,
      hrv: 52,
      spo2: 98,
      stress: 32,
      steps: 8420,
      sleep: 7.5,
      calories: 2100,
      respiration: 14,
      readiness: 78,
      status: "good",
      overtraining: false
    };
  }

  function enrichBiometrics(data: any) {
    const hrv = data.hrv || 50;
    const stress = data.stress || 40;
    const sleep = data.sleep || 7;
    const hr = data.heartRate || 70;

    let readiness = 50;
    readiness += hrv >= 55 ? 20 : (hrv >= 30 ? 10 : -10);
    readiness += stress < 45 ? 15 : (stress < 70 ? 0 : -15);
    readiness += sleep >= 7 ? 15 : (sleep >= 6 ? 8 : -15);
    readiness += hr < 100 ? 10 : -10;
    readiness = Math.min(100, Math.max(0, readiness));

    return {
      ...data,
      readiness,
      status: readiness >= 75 ? "excellent" : (readiness >= 50 ? "good" : "poor"),
      overtraining: hrv < 20 || (stress > 75 && hr > 80)
    };
  }

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();
