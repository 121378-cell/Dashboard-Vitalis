using Toybox.Application as App;
using Toybox.Communications as Comm;
using Toybox.WatchUi as Ui;
using Toybox.System as Sys;
using Toybox.UserProfile as Profile;
using Toybox.Timer as Timer;

// Persistence keys
const STORAGE_KEY = "atlas_readiness_data";
const CACHE_TIMESTAMP_KEY = "atlas_cache_ts";
var ATLAS_API_URL = "https://atlas-vitalis-backend.fly.dev/api/v1/readiness/score";
var ATLAS_SESSIONS_URL = "https://atlas-vitalis-backend.fly.dev/api/v1/sessions/today";

// Colors - Monochrome with yellow accent (!24bit: RRGGBB)
const COLOR_BG = 0x1A1A1A;
const COLOR_FG = 0xE0E0E0;
const COLOR_ACCENT = 0xE8FF47; // Yellow accent
const COLOR_GOOD = 0x4ADE80;
const COLOR_MODERATE = 0xFB923C;
const COLOR_POOR = 0xF87171;

// Constants
const CACHE_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const REQUEST_TIMEOUT_MS = 5000; // 5 seconds
const LOW_READINESS_THRESHOLD = 40;

class AtlasApp extends App.AppBase {
    var dataManager;
    var delegate;

    function initialize() {
        AppBase.initialize();
    }

    // onStart - Application starting
    function onStart(state) {
        dataManager = new DataManager();
        dataManager.loadCachedData();
        dataManager.fetchData();
    }

    // onStop - Application closing
    function onStop(state) {
        dataManager.stop();
    }

    // Return initial view
    function getInitialView() {
        delegate = new AtlasDelegate();
        return [new AtlasView(dataManager), delegate];
    }

    // Get data manager instance
    function getDataManager() {
        return dataManager;
    }
}

// Register application class
(:glance)
class AtlasAppDelegate extends App.AppDelegate {
}