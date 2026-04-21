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

# Aplicar fix a capacitor-health si es necesario
$pluginFile = "$ProjectRoot\node_modules\capacitor-health\android\src\main\java\com\fit_up\health\capacitor\HealthPlugin.kt"
if (Test-Path $pluginFile) {
    $content = Get-Content $pluginFile -Raw
    if ($content -match "dataOriginsFilter") {
        Write-Host "Aplicando fix a capacitor-health..." -ForegroundColor Yellow
        $content = $content.Replace("timeRangeSlicer = period,`r`n                dataOriginsFilter = dataOrigins", "timeRangeSlicer = period")
        $content = $content -replace 'if \(!hasPermission\(CapHealthPermission\.READ_STEPS\)\) \{\r?\n\s*call\.reject\("READ_STEPS permission not granted"\)\r?\n\s*return\r?\n\s*\}\r?\n\s*val startInstant', 'val startInstant'
        $content = $content -replace 'CoroutineScope\(Dispatchers\.IO\)\.launch \{\r?\n\s*try \{', "CoroutineScope(Dispatchers.IO).launch {`r`n                if (!hasPermission(CapHealthPermission.READ_STEPS)) {`r`n                    call.reject(`"READ_STEPS permission not granted`")`r`n                    return@launch`r`n                }`r`n                try {"
        Set-Content -Path $pluginFile -Value $content -NoNewline
        Write-Host "Fix aplicado" -ForegroundColor Green
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

$javaVersion = (Get-Command java).Source
Write-Host "Java: $javaVersion" -ForegroundColor DarkGray

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
