import { useState, useEffect } from 'react';
import { healthConnectService, HCPermissionStatus } from '../services/healthConnectService';

export function useHealthConnectPermissions() {
  const [granted, setGranted] = useState(false);
  const [permissions, setPermissions] = useState<Record<string, boolean>>({});

  const checkPermissions = async () => {
    const result = await healthConnectService.checkPermissions();
    setGranted(result.granted);
    setPermissions(result.permissions);
  };

  const requestPermissions = async () => {
    const result = await healthConnectService.requestPermissions();
    setGranted(result.granted);
    setPermissions(result.permissions);
  };

  useEffect(() => {
    checkPermissions();
  }, []);

  return { granted, permissions, requestPermissions, checkPermissions };
}
