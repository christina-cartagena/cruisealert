import api from "@/lib/axios";
import type { NotificationPreferences } from "./types";

export async function getPreferences(): Promise<NotificationPreferences> {
  const { data } = await api.get<NotificationPreferences>(
    "/notifications/preferences"
  );
  return data;
}

export async function updatePreferences(
  payload: Partial<NotificationPreferences>
): Promise<NotificationPreferences> {
  const { data } = await api.patch<NotificationPreferences>(
    "/notifications/preferences",
    payload
  );
  return data;
}

export async function sendPhoneVerification(
  phone_e164: string
): Promise<{ sent: boolean }> {
  const { data } = await api.post("/notifications/phone/send-verification", {
    phone_e164,
  });
  return data;
}

export async function checkPhoneVerification(
  phone_e164: string,
  code: string
): Promise<{ verified: boolean }> {
  const { data } = await api.post("/notifications/phone/check-verification", {
    phone_e164,
    code,
  });
  return data;
}
