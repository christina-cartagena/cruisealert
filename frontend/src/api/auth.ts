import api from "@/lib/axios";
import type { TokenResponse, RefreshResponse, AuthUserResponse } from "./types";

export async function register(
  email: string,
  password: string
): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/register", {
    email,
    password,
  });
  return data;
}

export async function login(
  email: string,
  password: string
): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/login", {
    email,
    password,
  });
  return data;
}

export async function refresh(): Promise<RefreshResponse> {
  const { data } = await api.post<RefreshResponse>("/auth/refresh", {});
  return data;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout", {});
}

export async function verifyEmail(token: string): Promise<{ ok: boolean }> {
  const { data } = await api.get("/auth/verify-email", { params: { token } });
  return data;
}

export async function getMe(): Promise<AuthUserResponse> {
  const { data } = await api.get<AuthUserResponse>("/users/me");
  return data;
}
