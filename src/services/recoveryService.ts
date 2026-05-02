import api from "./api";
import type {
  RecoveryStatus,
  RecoverySessionData,
  InjuryRecord,
  InjuryPatternsResponse,
  PainReport,
} from "../types";

export const recoveryService = {
  getStatus: () =>
    api.get<{ alert_level: string; alerts: RecoveryStatus["alerts"]; readiness_penalty: number; active_injuries: RecoveryStatus["active_injuries"]; zones_to_avoid: string[]; recommendations: string[]; forecast_risk: number }>("/recovery/status"),

  getSession: () =>
    api.get<RecoverySessionData>("/recovery/session"),

  reportPain: (data: PainReport) =>
    api.post<{ status: string; injury: Record<string, unknown>; message: string; zones_to_avoid: string[] }>("/recovery/report-pain", data),

  getInjuryHistory: () =>
    api.get<InjuryRecord[]>("/recovery/injury-history"),

  getInjuryPatterns: () =>
    api.get<InjuryPatternsResponse>("/recovery/injury-patterns"),

  acknowledgeAlert: (data: { alert_indicator: string; alert_reason: string; user_action: string }) =>
    api.post<{ status: string; indicator: string; user_action: string; message: string }>("/recovery/acknowledge-alert", data),

  getBodyZones: () =>
    api.get<{ zones: string[] }>("/recovery/body-zones"),

  getZoneExercises: (zone: string) =>
    api.get<{ zone: string; alternative_exercises: string[] }>(`/recovery/zone-exercises/${zone}`),
};
