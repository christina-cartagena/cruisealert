import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import * as authApi from "@/api/auth";
import { toast } from "@/hooks/use-toast";

export function useLogin() {
  const navigate = useNavigate();
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const setUser = useAuthStore((s) => s.setUser);
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.login(email, password),
    onSuccess: (data) => {
      setAccessToken(data.access_token);
      setUser({
        id: data.user.id,
        email: data.user.email,
        tier: data.user.tier,
      });
      navigate("/search");
    },
    onError: () =>
      toast({
        title: "Login failed",
        description: "Check your email and password and try again.",
        variant: "destructive",
      }),
  });
}

export function useRegister() {
  const navigate = useNavigate();
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const setUser = useAuthStore((s) => s.setUser);
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.register(email, password),
    onSuccess: (data) => {
      setAccessToken(data.access_token);
      setUser({
        id: data.user.id,
        email: data.user.email,
        tier: data.user.tier,
      });
      toast({
        title: "Account created",
        description: "Check your inbox to verify your email address.",
      });
      navigate("/verify-email");
    },
    onError: () =>
      toast({
        title: "Registration failed",
        description: "That email may already be registered.",
        variant: "destructive",
      }),
  });
}

export function useLogout() {
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);
  return useMutation({
    mutationFn: () => authApi.logout(),
    onSettled: () => {
      logout();
      navigate("/login");
    },
  });
}
