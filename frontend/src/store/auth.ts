import { create } from "zustand";

export type Tier = "free" | "pro";

export interface AuthUser {
  id: string;
  email: string;
  tier: Tier;
}

interface AuthState {
  // Access token is held in MEMORY ONLY — never persisted to
  // localStorage/sessionStorage. The refresh token lives in an httpOnly cookie.
  accessToken: string | null;
  user: AuthUser | null;
  setAccessToken: (token: string) => void;
  setUser: (user: AuthUser | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  setAccessToken: (token) => set({ accessToken: token }),
  setUser: (user) => set({ user }),
  logout: () => set({ accessToken: null, user: null }),
}));
