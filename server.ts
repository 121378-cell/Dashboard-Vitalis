import express, { Request, Response, NextFunction } from "express";
import { createServer as createViteServer } from "vite";
import path from "path";
import { fileURLToPath } from "url";
import cors from "cors";
import dotenv from "dotenv";
import { createRequire } from "module";
const require = createRequire(import.meta.url);
const { GarminConnect } = require("garmin-connect");
import axios from "axios";
import asyncHandler from "express-async-handler";

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(cors());
  app.use(express.json());

  // Garmin Sync API
  app.post("/api/sync/garmin", asyncHandler(async (req, res) => {
    const { email, password } = req.body;
    const userEmail = email || process.env.GARMIN_EMAIL;
    const userPassword = password || process.env.GARMIN_PASSWORD;

    if (!userEmail || !userPassword || userEmail.trim() === "" || userPassword.trim() === "") {
      res.status(400).json({ 
        success: false, 
        error: "Garmin credentials missing. Please set GARMIN_EMAIL and GARMIN_PASSWORD in the Secrets panel." 
      });
      return;
    }

    console.log("Starting Garmin sync for:", userEmail);
    
    try {
      const client = new GarminConnect();
      await client.login(userEmail, userPassword);
      console.log("Garmin login successful");
      
      const today = new Date();
      const heartRate = await client.getHeartRate(today);
      const sleep = await client.getSleepData(today);
      console.log("Garmin data fetched successfully");

      res.json({
        success: true,
        data: {
          heartRate,
          sleep
        }
      });
    } catch (error: any) {
      console.error("Garmin sync error details:", error);
      res.status(500).json({ 
        success: false, 
        error: error?.message || "Failed to sync with Garmin. Check credentials or MFA." 
      });
    }
  }));

  // wger Sync API
  app.post("/api/sync/wger", asyncHandler(async (req, res) => {
    const apiKey = process.env.WGER_API_KEY;
    if (!apiKey || apiKey.trim() === "") {
      res.status(400).json({ success: false, error: "wger API key missing. Please set WGER_API_KEY in the Secrets panel." });
      return;
    }

    try {
      // Using workoutlog to get actual training sessions
      const response = await axios.get("https://wger.de/api/v2/workoutlog/", {
        headers: { "Authorization": `Token ${apiKey}` },
        timeout: 10000
      });

      res.json({
        success: true,
        data: response.data.results || response.data
      });
    } catch (error: any) {
      console.error("wger sync error:", error?.message);
      // If workoutlog 404s, fallback to workout
      if (error?.response?.status === 404) {
        try {
          const fallback = await axios.get("https://wger.de/api/v2/workout/", {
            headers: { "Authorization": `Token ${apiKey}` },
            timeout: 10000
          });
          res.json({
            success: true,
            data: fallback.data.results || fallback.data
          });
          return;
        } catch (fallbackError: any) {
          console.error("wger fallback error:", fallbackError?.message);
        }
      }
      
      res.status(500).json({ 
        success: false, 
        error: error?.response?.data?.detail || error?.message || "Failed to sync with wger" 
      });
    }
  }));

  // Global Error Handler
  app.use((err: any, req: Request, res: Response, next: NextFunction) => {
    console.error("Global error:", err);
    res.status(500).json({
      success: false,
      error: err.message || "Internal Server Error"
    });
  });

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
