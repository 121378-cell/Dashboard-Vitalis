using Toybox.Graphics as Gfx;
using Toybox.WatchUi as Ui;
using Toybox.System as Sys;
using Toybox.Lang;
using Toybox.Timer as Timer;
using Toybox.Application as App;

class AtlasView extends Ui.View {
    var dataManager;
    var readinessScore;
    var readinessStatus;
    var hrvValue;
    var hrValue;
    var sleepValue;
    var recommendation;
    var overtrainingRisk;
    var lastUpdateTime;

    function initialize(dm) {
        View.initialize();
        dataManager = dm;
        readinessScore = 0;
        readinessStatus = "";
        hrvValue = "--";
        hrValue = "--";
        sleepValue = "--";
        recommendation = "Cargando...";
        overtrainingRisk = false;
        lastUpdateTime = null;
    }

    // onUpdate - Called when view needs to refresh
    function onUpdate(dc) {
        View.onUpdate(dc);

        var data = dataManager.currentData;
        if (data != null) {
            readinessScore = data.score != null ? data.score : 0;
            readinessStatus = data.status != null ? data.status : "--";
            hrvValue = data.hrv != null ? data.hrv.toString() : "--";
            hrValue = data.hr != null ? data.hr.toString() : "--";
            sleepValue = data.sleep != null ? data.sleep.toString() : "--";
            recommendation = data.recommendation != null ? data.recommendation : "--";
            overtrainingRisk = data.overtraining_risk != null ? data.overtraining_risk : false;
            lastUpdateTime = data.timestamp;
        }

        // Get display dimensions
        var w = dc.getWidth();
        var h = dc.getHeight();
        var cx = w / 2;
        var cy = h / 2;

        // Clear background
        dc.setColor(COLOR_BG, COLOR_BG);
        dc.clear();

        // Get accent color for readiness
        var readinessColor = getReadinessColor(readinessScore);

        // Draw header
        dc.setColor(COLOR_ACCENT, Gfx.COLOR_TRANSPARENT);
        dc.setFont(Gfx.FONT_TINY);
        dc.drawText(cx, 4, Gfx.TEXT_JUSTIFY_CENTER, "⚡ ATLAS");

        // Draw readiness label
        dc.setColor(COLOR_FG, Gfx.COLOR_TRANSPARENT);
        dc.setFont(Gfx.FONT_SMALL);
        dc.drawText(cx, 20, Gfx.TEXT_JUSTIFY_CENTER, "READINESS");

        // Draw large score circle / semi-circle gauge
        var gaugeRadius = 38;
        var gaugeY = 68;
        drawSemiCircleGauge(dc, cx, gaugeY, gaugeRadius, readinessScore, readinessColor);

        // Draw score number large
        dc.setColor(COLOR_FG, Gfx.COLOR_TRANSPARENT);
        dc.setFont(Gfx.FONT_NUMBER_MILD);
        var scoreStr = readinessScore.toString();
        var scoreW = dc.getTextWidthInPixels(scoreStr, Gfx.FONT_NUMBER_MILD);
        dc.drawText(cx - scoreW/2, gaugeY - 12, Gfx.TEXT_JUSTIFY_CENTER, scoreStr);

        // Draw status text below score
        dc.setFont(Gfx.FONT_TINY);
        var statusUpper = readinessStatus.toUpper();
        dc.drawText(cx, gaugeY + 22, Gfx.TEXT_JUSTIFY_CENTER, statusUpper);

        // Draw metrics line below
        var metricsY = 98;
        dc.setFont(Gfx.FONT_SMALL);
        dc.setColor(COLOR_FG, Gfx.COLOR_TRANSPARENT);

        // HRV metric
        dc.drawText(24, metricsY, Gfx.TEXT_JUSTIFY_LEFT, "HRV:");
        dc.setColor(COLOR_ACCENT, Gfx.COLOR_TRANSPARENT);
        var hrvStr = hrvValue + "ms";
        dc.drawText(24 + dc.getTextWidthInPixels("HRV:", Gfx.FONT_SMALL) + 2, metricsY, Gfx.TEXT_JUSTIFY_LEFT, hrvStr);

        // HR metric
        dc.setColor(COLOR_FG, Gfx.COLOR_TRANSPARENT);
        var hrLabel = " HR:";
        dc.drawText(68, metricsY, Gfx.TEXT_JUSTIFY_LEFT, hrLabel);
        dc.setColor(COLOR_ACCENT, Gfx.COLOR_TRANSPARENT);
        var hrStr = hrValue + "";
        dc.drawText(68 + dc.getTextWidthInPixels(hrLabel, Gfx.FONT_SMALL) + 2, metricsY, Gfx.TEXT_JUSTIFY_LEFT, hrStr);

        // Sleep metric
        dc.setColor(COLOR_FG, Gfx.COLOR_TRANSPARENT);
        var sleepLabel = "  SUEÑO:";
        dc.drawText(cx + 10, metricsY, Gfx.TEXT_JUSTIFY_LEFT, sleepLabel);
        dc.setColor(COLOR_ACCENT, Gfx.COLOR_TRANSPARENT);
        var sleepStr = sleepValue + "h";
        dc.drawText(cx + 10 + dc.getTextWidthInPixels(sleepLabel, Gfx.FONT_SMALL) + 2, metricsY, Gfx.TEXT_JUSTIFY_LEFT, sleepStr);

        // Bottom section - recommendation
        var bottomY = 118;
        dc.setColor(COLOR_FG, Gfx.COLOR_TRANSPARENT);
        dc.setFont(Gfx.FONT_TINY);
        dc.drawText(cx, bottomY, Gfx.TEXT_JUSTIFY_CENTER, "HOY");

        bottomY += 14;
        dc.setColor(COLOR_ACCENT, Gfx.COLOR_TRANSPARENT);
        dc.setFont(Gfx.FONT_SMALL);
        if (recommendation.length() > 20) {
            recommendation = recommendation.substring(0, 18) + "...";
        }
        dc.drawText(cx, bottomY, Gfx.TEXT_JUSTIFY_CENTER, recommendation);

        // Overtraining warning badge
        if (overtrainingRisk) {
            dc.setColor(0xF87171, Gfx.COLOR_TRANSPARENT);
            dc.setFont(Gfx.FONT_TINY);
            dc.drawText(cx, h - 16, Gfx.TEXT_JUSTIFY_CENTER, "⚠️ RIESGO SOBREENTRENAMIENTO");
        }

        // Data age indicator
        if (lastUpdateTime != null) {
            dc.setColor(COLOR_FG, Gfx.COLOR_TRANSPARENT);
            dc.setFont(Gfx.FONT_TINY);
            dc.drawText(w - 2, h - 2, Gfx.TEXT_JUSTIFY_RIGHT, "*");
        }
    }

    // Draw semi-circular readiness gauge
    function drawSemiCircleGauge(dc, cx, cy, radius, score, color) {
        var maxAngle = 3.5; // Semi-circle arc angle in radians (~200 degrees)
        var startAngle = 3.14159 + (3.14159 - maxAngle) / 2.0;
        var endAngle = startAngle + maxAngle;

        // Background arc
        dc.setColor(0x333333, Gfx.COLOR_TRANSPARENT);
        dc.setPenWidth(6);
        dc.drawArc(cx, cy, radius, Gfx.ARC_CLOCKWISE, startAngle, endAngle);

        // Progress arc
        var progressAngle = startAngle + (maxAngle * (score / 100.0));
        dc.setColor(color, Gfx.COLOR_TRANSPARENT);
        dc.setPenWidth(6);
        dc.drawArc(cx, cy, radius, Gfx.ARC_CLOCKWISE, startAngle, progressAngle);

        // Tick marks for score levels
        dc.setColor(0x444444, Gfx.COLOR_TRANSPARENT);
        dc.setPenWidth(2);
        for (var i = 0; i <= 10; i++) {
            var tickAngle = startAngle + (maxAngle * (i / 10.0));
            var tickInner = radius - 4;
            var tickOuter = radius + 4;
            var x1 = cx + tickInner * Math.sin(tickAngle);
            var y1 = cy - tickInner * Math.cos(tickAngle);
            var x2 = cx + tickOuter * Math.sin(tickAngle);
            var y2 = cy - tickOuter * Math.cos(tickAngle);
            dc.drawLine(x1, y1, x2, y2);
        }

        // Highlight every 5 ticks
        dc.setColor(0x666666, Gfx.COLOR_TRANSPARENT);
        dc.setPenWidth(3);
        for (var i = 0; i <= 10; i += 5) {
            var tickAngle = startAngle + (maxAngle * (i / 10.0));
            var tickInner = radius - 5;
            var tickOuter = radius + 5;
            var x1 = cx + tickInner * Math.sin(tickAngle);
            var y1 = cy - tickInner * Math.cos(tickAngle);
            var x2 = cx + tickOuter * Math.sin(tickAngle);
            var y2 = cy - tickOuter * Math.cos(tickAngle);
            dc.drawLine(x1, y1, x2, y2);
        }
    }

    // Get color based on readiness score
    function getReadinessColor(score) {
        if (score >= 85) {
            return COLOR_GOOD;
        } else if (score >= 70) {
            return COLOR_ACCENT;
        } else if (score >= 50) {
            return COLOR_MODERATE;
        } else {
            return COLOR_POOR;
        }
    }
}

// Delegate for input handling
class AtlasDelegate extends Ui.BehaviorDelegate {
    var dataManager;

    function initialize() {
        BehaviorDelegate.initialize();
        dataManager = App.getApp().getDataManager();
    }

    // Enter key - refresh data
    function onSelect() {
        dataManager.fetchData();
        Ui.requestUpdate();
        return true;
    }

    // Up swipe - refresh
    function onNextPage() {
        dataManager.fetchData();
        Ui.requestUpdate();
        return true;
    }

    // Down swipe - refresh
    function onPreviousPage() {
        dataManager.fetchData();
        Ui.requestUpdate();
        return true;
    }

    // Menu/back key - exit
    function onBack() {
        Ui.popView(Ui.SLIDE_IMMEDIATE);
        return true;
    }
}
