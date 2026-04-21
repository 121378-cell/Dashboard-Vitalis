#!/usr/bin/env pwsh
param(
    [switch]$Clean,
    [switch]$Install
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "Continue"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$AndroidSdk = "$env:USERPROFILE\AndroidSDK"
$JdkPath = "$AndroidSdk\jdk21.0.10_7"
$ApkOutput = "$ProjectRoot\android\app\build\outputs\apk\debug\app-debug.apk"

Write-Host "=== Vitalis Android Build ===" -ForegroundColor Cyan

# Aplicar fixes a capacitor-health si es necesario
$pluginFile = "$ProjectRoot\node_modules\capacitor-health\android\src\main\java\com\fit_up\health\capacitor\HealthPlugin.kt"
$pluginBuildFile = "$ProjectRoot\node_modules\capacitor-health\android\build.gradle"

if (Test-Path $pluginFile) {
    $content = Get-Content $pluginFile -Raw
    $needsFix = $false
    
    # Fix 1: dataOriginsFilter
    if ($content -match "dataOriginsFilter") {
        Write-Host "Fix 1: dataOriginsFilter..." -ForegroundColor Yellow
        $content = $content.Replace("timeRangeSlicer = period,`n                dataOriginsFilter = dataOrigins", "timeRangeSlicer = period")
        $needsFix = $true
    }
    
    # Fix 2: hasPermission suspend function
    if ($content -match "if \(!hasPermission\(CapHealthPermission.READ_STEPS\)\)") {
        Write-Host "Fix 2: hasPermission..." -ForegroundColor Yellow
        $oldCode = @"
            if (!hasPermission(CapHealthPermission.READ_STEPS)) {
                call.reject("READ_STEPS permission not granted")
                return
            }

            val startInstant = Instant.parse(startDate)
            val endInstant = Instant.parse(endDate)
            val timeRange = TimeRangeFilter.between(startInstant, endInstant)
            val request = ReadRecordsRequest(StepsRecord::class, timeRange)

            CoroutineScope(Dispatchers.IO).launch {
                try {
"@
        $newCode = @"
            val startInstant = Instant.parse(startDate)
            val endInstant = Instant.parse(endDate)
            val timeRange = TimeRangeFilter.between(startInstant, endInstant)
            val request = ReadRecordsRequest(StepsRecord::class, timeRange)

            CoroutineScope(Dispatchers.IO).launch {
                if (!hasPermission(CapHealthPermission.READ_STEPS)) {
                    call.reject("READ_STEPS permission not granted")
                    return@launch
                }
                try {
"@
        $content = $content.Replace($oldCode, $newCode)
        $needsFix = $true
    }
    
    if ($needsFix) {
        Set-Content -Path $pluginFile -Value $content -NoNewline
        Write-Host "Fixes aplicados a capacitor-health" -ForegroundColor Green
    }
}

if (Test-Path $pluginBuildFile) {
    $buildContent = Get-Content $pluginBuildFile -Raw
    if ($buildContent -match "proguard-android.txt") {
        Write-Host "Fix proguard..." -ForegroundColor Yellow
        $buildContent = $buildContent.Replace("getDefaultProguardFile('proguard-android.txt')", "getDefaultProguardFile('proguard-android-optimize.txt')")
        Set-Content -Path $pluginBuildFile -Value $buildContent -NoNewline
        Write-Host "Fix proguard aplicado" -ForegroundColor Green
    }
}

if (-not (Test-Path $JdkPath)) {
    Write-Error "JDK no encontrado: $JdkPath"
    exit 1
}

if (-not $env:ANDROID_HOME) {
    $env:ANDROID_HOME = $AndroidSdk
}

$env:JAVA_HOME = $JdkPath
$env:PATH = "$JdkPath\bin;$env:PATH"

$javaPath = (Get-Command java).Source
Write-Host "Java: $javaPath" -ForegroundColor DarkGray

Write-Host "Building web..." -ForegroundColor Green
Set-Location $ProjectRoot
npm run build
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "Syncing Capacitor..." -ForegroundColor Green
npx cap sync android
if ($LASTEXITCODE -ne 0) { exit 1 }

if ($Clean) {
    Write-Host "Cleaning..." -ForegroundColor Green
    Set-Location "$ProjectRoot\android"
    .\gradlew clean --no-daemon
}

Write-Host "Building APK..." -ForegroundColor Green
Set-Location "$ProjectRoot\android"
.\gradlew assembleDebug --no-daemon
if ($LASTEXITCODE -ne 0) { exit 1 }

if (Test-Path $ApkOutput) {
    $apkSize = (Get-Item $ApkOutput).Length / 1MB
    Write-Host "BUILD OK: $ApkOutput ($([math]::Round($apkSize, 2)) MB)" -ForegroundColor Green
    
    if ($Install) {
        $adb = "$AndroidSdk\platform-tools\adb.exe"
        if (Test-Path $adb) {
            & $adb install -r $ApkOutput
        }
    }
} else {
    Write-Error "APK no encontrado"
    exit 1
}

Set-Location $ProjectRoot
