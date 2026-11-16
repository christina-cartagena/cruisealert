import api from "@/lib/axios";
import type { Alert, CreateAlertPayload, UpdateAlertPayload } from "./types";

export async function listAlerts(): Promise<Alert[]> {
  const { data } = await api.get<Alert[]>("/alerts");
  return data;
}

export async function createAlert(
  payload: CreateAlertPayload
): Promise<Alert> {
  const { data } = await api.post<Alert>("/alerts", payload);
  return data;
}

export async function updateAlert(
  id: string,
  payload: UpdateAlertPayload
): Promise<Alert> {
  const { data } = await api.patch<Alert>(`/alerts/${id}`, payload);
  return data;
}

export async function deleteAlert(id: string): Promise<void> {
  await api.delete(`/alerts/${id}`);
}

export async function deleteAlerts(ids: string[]): Promise<void> {
  await Promise.all(ids.map((id) => deleteAlert(id)));
}
