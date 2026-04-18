import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.vitalis.app',
  appName: 'Vitalis',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
    cleartext: true,
    allowNavigation: [
      'api.groq.com',
      '*.google.com',
      '192.168.1.*',
      'localhost'
    ]
  }
};

export default config;
