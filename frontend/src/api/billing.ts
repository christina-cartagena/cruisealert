import api from "@/lib/axios";
import type {
  CheckoutSessionResponse,
  PortalSessionResponse,
  BillingPlan,
} from "./types";

export async function createCheckoutSession(
  plan: BillingPlan
): Promise<CheckoutSessionResponse> {
  const { data } = await api.post<CheckoutSessionResponse>(
    "/billing/create-checkout-session",
    { plan }
  );
  return data;
}

export async function createPortalSession(): Promise<PortalSessionResponse> {
  const { data } = await api.post<PortalSessionResponse>(
    "/billing/portal-session",
    {}
  );
  return data;
}
