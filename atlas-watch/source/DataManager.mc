using Toybox.Application as App;
using Toybox.Communications as Comm;
using Toybox.System as Sys;
using Toybox.Timer as Timer;
using Toybox.UserProfile as Profile;
using Lang;

// Communication response callback
function commCallback(responseCode as Number, data as Dictionary?) as Void {
    var app = App.getApp();
    var dm = app.getDataManager();
    dm.handleResponse(responseCode, data);
}

// Data Manager - handles all data fetching and caching
class DataManager {
    hidden var timer;
    hidden var currentData;
    hidden var isRefreshing;
    var userId;

    function initialize() {
        timer = new Timer.Timer();
        currentData = {};
        isRefreshing = false;
        userId = "default_user";
    }

    // Start periodic refresh
    function start() {
        // Refresh every 30 minutes
        timer.start(method(:onTimerTick), 30 * 60 * 1000, true);
    }

    // Stop timer
    function stop() {
        timer.stop();
    }

    // Timer callback
    function onTimerTick() {
        fetchData();
    }

    // Main data fetch
    function fetchData() {
        if (isRefreshing) {
            return;
        }

        // Check network availability
        if (!System has :ServiceDelegate) {
            // Simulator or no network - try cached data
            loadCachedData();
            triggerUpdate();
            return;
        }

        // Check if we have network
        var networkAccess = Communications has :getNetworkAccess;
        if (networkAccess != null && !networkAccess.call()) {
            // No network, use cache
            loadCachedData();
            triggerUpdate();
            return;
        }

        isRefreshing = true;

        // Prepare request options
        var options = new Comm.RequestOptions();
        options.method = Comm.HTTP_REQUEST_METHOD_GET;
        options.responseType = Comm.HTTP_RESPONSE_CONTENT_TYPE_JSON;

        // Headers
        var headers = {
            "x-user-id" => userId,
            "Content-Type" => "application/json"
        };
        options.headers = headers;
        options.timeout = 5000; // 5 seconds

        // Make readiness request
        var readyUrl = "https://atlas-vitalis-backend.fly.dev/api/v1/readiness/score";
        try {
            Communications.makeWebRequest(readyUrl, {}, options, method(:onReadyResponse));
        } catch (e) {
            Sys.println("Ready request error: " + e);
            isRefreshing = false;
            loadCachedData();
            triggerUpdate();
        }
    }

    // Handle readiness response
    function onReadyResponse(responseCode as Number, data as Dictionary?) {
        if (responseCode == 200 && data != null) {
            parseReadyData(data);
            cacheData(data);
            triggerUpdate();

            // Now fetch sessions data
            fetchSessions();
        } else {
            Sys.println("Ready response error: " + responseCode);
            loadCachedData();
            triggerUpdate();
        }
        isRefreshing = false;
    }

    // Parse readiness data
    function parseReadyData(data as Dictionary) {
        var parsed = {};

        // Score
        parsed["score"] = data.get("score");

        // Status
        var statusMap = {
            "excellent" => "EXCELENTE",
            "good" => "BUENO",
            "moderate" => "MODERADO",
            "poor" => "BAJO",
            "rest" => "DESCANSO",
            "no_data" => "SIN DATOS"
        };
        var status = data.get("status");
        if (status != null) {
            var mapped = statusMap.get(status);
            parsed["status"] = mapped != null ? mapped : status.toUpper();
        } else {
            parsed["status"] = "--";
        }

        // Components
        var comp = data.get("components");
        if (comp != null) {
            parsed["hrv"] = comp.get("hrv");
            parsed["rhr"] = comp.get("rhr");
            parsed["sleep"] = comp.get("sleep");
        } else {
            parsed["hrv"] = null;
            parsed["rhr"] = null;
            parsed["sleep"] = null;
        }

        // Recommendation
        parsed["recommendation"] = data.get("recommendation");

        // Overtraining risk
        parsed["overtraining_risk"] = data.get("overtraining_risk");
        if (parsed["overtraining_risk"] == true) {
            // Vibrate for overtraining risk
            if (Toybox has :SensorHistory) {
                // Try to vibrate
                try {
                    Toybox.vibrate([new Vibra.VibePattern([new Vibra.VibeProfile(50, 500)])]);
                } catch (e) {
                }
            }
        }

        // Timestamp
        parsed["timestamp"] = data.get("date");

        // HR from rhr
        if (parsed["rhr"] != null) {
            parsed["hr"] = parsed["rhr"];
        } else if (comp != null && comp.get("hr") != null) {
            parsed["hr"] = comp.get("hr");
        } else {
            parsed["hr"] = null;
        }

        currentData = parsed;
    }

    // Fetch sessions for today
    function fetchSessions() {
        var options = new Comm.RequestOptions();
        options.method = Comm.HTTP_REQUEST_METHOD_GET;
        options.responseType = Comm.HTTP_RESPONSE_CONTENT_TYPE_JSON;
        var headers = {"x-user-id" => userId, "Content-Type" => "application/json"};
        options.headers = headers;
        options.timeout = 5000;

        var url = "https://atlas-vitalis-backend.fly.dev/api/v1/sessions/today";
        try {
            Communications.makeWebRequest(url, {}, options, method(:onSessionsResponse));
        } catch (e) {
            // Ignore sessions errors
        }
    }

    // Handle sessions response
    function onSessionsResponse(responseCode as Number, data as Dictionary?) {
        // Store in cache if needed
        if (responseCode == 200 && data != null) {
            var app = App.getApp();
            var cache = app.getProperty("sessions_cache");
            if (cache == null) {
                cache = {};
            }
            cache["today"] = data;
            app.setProperty("sessions_cache", cache);
        }
    }

    // Cache data to persistent storage
    function cacheData(data as Dictionary) {
        var app = App.getApp();
        app.setProperty("atlas_cache_data", data);
        app.setProperty("atlas_cache_ts", System.getClockTime());
    }

    // Load cached data
    function loadCachedData() {
        var app = App.getApp();
        var cached = app.getProperty("atlas_cache_data");
        if (cached != null) {
            parseReadyData(cached);
        } else {
            currentData = {
                "score" => 0,
                "status" => "SIN DATOS",
                "hrv" => null,
                "hr" => null,
                "rhr" => null,
                "sleep" => null,
                "recommendation" => "Sincroniza datos",
                "overtraining_risk" => false,
                "timestamp" => null
            };
        }
    }

    // Trigger UI update
    function triggerUpdate() {
        Ui.requestUpdate();
    }

    // Get current data
    function getCurrentData() {
        return currentData;
    }

    // Get readiness score
    function getReadinessScore() {
        return currentData.get("score");
    }
}
