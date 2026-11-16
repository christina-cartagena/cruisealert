// TypeScript types mirroring the backend response schemas (spec Step 9).

export type Tier = "free" | "pro";

export type CabinType = "interior" | "oceanview" | "balcony" | "suite";

export type CruiseLine =
  | "royal_caribbean"
  | "carnival"
  | "norwegian"
  | "celebrity"
  | "princess"
  | "msc"
  | "holland_america"
  | "disney"
  | "virgin_voyages";

export type PriceTrend = "down" | "up" | "stable";

export type TriggerType =
  | "price_drop"
  | "back_in_stock"
  | "availability_threshold";

export type AlertStatus = "active" | "paused" | "fired" | "expired";

// ---- Auth ----
export interface AuthUserResponse {
  id: string;
  email: string;
  tier: Tier;
  email_verified: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUserResponse;
}

export interface RefreshResponse {
  access_token: string;
  token_type: string;
}

// ---- Sailings ----
export interface CabinPrice {
  cabin_type: CabinType;
  price_usd: string;
  price_local: string | null;
  currency_code: string;
  cabins_available: number | null;
  recorded_at: string;
}

export interface SailingListItem {
  id: string;
  cruise_line: CruiseLine;
  market: string;
  ship_name: string;
  destination_region: string;
  departure_port: string;
  departure_date: string;
  return_date: string;
  duration_nights: number;
  ship_image_url: string | null;
  booking_url: string | null;
  lowest_price_usd: string | null;
  lowest_cabin_type: CabinType | null;
  price_trend: PriceTrend;
}

export interface SailingListResponse {
  items: SailingListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface PriceHistoryPoint {
  recorded_at: string; // ISO date/datetime
  price_usd: string;
  cabins_available: number | null;
}

export interface CabinDetail {
  cabin_type: CabinType;
  current_price_usd: string | null;
  current_price_local: string | null;
  currency_code: string | null;
  cabins_available: number | null;
  price_trend: PriceTrend;
  history: PriceHistoryPoint[];
}

export interface SailingDetailResponse {
  id: string;
  cruise_line: CruiseLine;
  market: string;
  ship_name: string;
  destination_region: string;
  departure_port: string;
  departure_date: string;
  return_date: string;
  duration_nights: number;
  itinerary_ports: string[];
  ship_image_url: string | null;
  booking_url: string | null;
  cabins: CabinDetail[];
  // history_days reflects the tier cap the server applied (7 free / 90 pro)
  history_days: number;
}

// ---- Alerts ----
export interface Alert {
  id: string;
  sailing_id: string;
  ship_name: string;
  cruise_line: CruiseLine;
  destination_region: string;
  departure_date: string;
  cabin_type: CabinType;
  trigger_type: TriggerType;
  threshold_pct: string | null;
  threshold_count: number | null;
  email_enabled: boolean;
  sms_enabled: boolean;
  status: AlertStatus;
  last_checked_at: string | null;
  last_fired_at: string | null;
  created_at: string;
}

export interface CreateAlertPayload {
  sailing_id: string;
  cabin_type: CabinType;
  trigger_type: TriggerType;
  threshold_pct?: number | null;
  threshold_count?: number | null;
  email_enabled: boolean;
  sms_enabled: boolean;
}

export interface UpdateAlertPayload {
  threshold_pct?: number | null;
  threshold_count?: number | null;
  status?: AlertStatus;
  email_enabled?: boolean;
  sms_enabled?: boolean;
}

// Returned with HTTP 403 when the free-tier alert cap is hit.
export interface AlertLimitError {
  code: "alert_limit_reached";
  message: string;
  upgrade_url: string;
}

export interface ProRequiredError {
  code: "pro_required";
  message: string;
}

// ---- Billing ----
export interface CheckoutSessionResponse {
  url: string;
}
export interface PortalSessionResponse {
  url: string;
}
export type BillingPlan = "monthly" | "annual";

// ---- Notifications ----
export interface NotificationPreferences {
  email_enabled: boolean;
  sms_enabled: boolean;
  phone_e164: string | null;
  phone_verified: boolean;
  phone_verified_at: string | null;
}
