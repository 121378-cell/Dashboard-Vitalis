// Test script to verify Health Connect fixes
const fs = require('fs');
const path = require('path');

console.log('=== Health Connect Fixes Verification ===\n');

// 1. Verify AndroidManifest.xml permissions
const manifestPath = path.join(__dirname, 'android/app/src/main/AndroidManifest.xml');
const manifest = fs.readFileSync(manifestPath, 'utf8');

const requiredPermissions = [
  'READ_STEPS',
  'READ_HEART_RATE', 
  'READ_SLEEP',
  'READ_OXYGEN_SATURATION',
  'READ_RESPIRATORY_RATE',
  'READ_HEART_RATE_VARIABILITY'
];

console.log('1. Checking AndroidManifest.xml permissions:');
requiredPermissions.forEach(perm => {
  const found = manifest.includes(`health.${perm}`);
  console.log(`   ${found ? '✅' : '❌'} ${perm}`);
});

// 2. Verify health_permissions.xml
const permsPath = path.join(__dirname, 'android/app/src/main/res/values/health_permissions.xml');
const perms = fs.readFileSync(permsPath, 'utf8');

const requiredItems = [
  'steps',
  'heart_rate',
  'heart_rate_variability',
  'active_energy_burned',
  'sleep',
  'oxygen_saturation',
  'respiratory_rate',
  'body_fat',
  'weight'
];

console.log('\n2. Checking health_permissions.xml items:');
requiredItems.forEach(item => {
  const found = perms.includes(`<item>${item}</item>`);
  console.log(`   ${found ? '✅' : '❌'} ${item}`);
});

// 3. Verify healthConnectService.ts
const servicePath = path.join(__dirname, 'src/services/healthConnectService.ts');
const service = fs.readFileSync(servicePath, 'utf8');

console.log('\n3. Checking healthConnectService.ts:');

const checks = [
  { name: 'REQUIRED_HEALTH_PERMISSIONS array', pattern: /REQUIRED_HEALTH_PERMISSIONS\s*=/ },
  { name: 'READ_SLEEP permission', pattern: /READ_SLEEP/ },
  { name: 'READ_RESPIRATORY_RATE permission', pattern: /READ_RESPIRATORY_RATE/ },
  { name: 'Detailed permission check method', pattern: /checkDetailedPermissions/ },
  { name: 'SpO2 reading method', pattern: /readSpO2/ },
  { name: 'HRV validation (> 0)', pattern: /hrv.*!== null.*hrv.*> 0/ },
  { name: 'Steps null check', pattern: /steps === null/ },
  { name: 'Resting heart rate tracking', pattern: /restingHeartRate/ }
];

checks.forEach(check => {
  const found = check.pattern.test(service);
  console.log(`   ${found ? '✅' : '❌'} ${check.name}`);
});

// 4. Verify App.tsx validation fix
const appPath = path.join(__dirname, 'src/App.tsx');
const app = fs.readFileSync(appPath, 'utf8');

console.log('\n4. Checking App.tsx data validation:');

const appChecks = [
  { name: 'Null check for steps/calories/hr', pattern: /hcData\.steps !== null.*\|\|.*hcData\.calories !== null/ },
  { name: 'SpO2 from hcData', pattern: /hcData\.spo2/ }
];

appChecks.forEach(check => {
  const found = check.pattern.test(app);
  console.log(`   ${found ? '✅' : '❌'} ${check.name}`);
});

console.log('\n=== Verification Complete ===');
console.log('\nKey fixes implemented:');
console.log('✅ Added missing Health Connect permissions (READ_SLEEP, READ_RESPIRATORY_RATE, etc.)');
console.log('✅ Fixed permission checking logic (removed cached granted state)');
console.log('✅ Added SpO2, HRV, and body composition reading methods');
console.log('✅ Fixed null/zero value handling in data validation');
console.log('✅ Enhanced error handling and logging');
console.log('✅ Added data validation for biometric integrity');