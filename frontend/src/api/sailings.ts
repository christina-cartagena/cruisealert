import api from "@/lib/axios";
import type {
  SailingListResponse,
  SailingDetailResponse,
  CruiseLine,
  CabinType,
} from "./types";

export interface SailingFilterParams {
  cruise_line?: CruiseLine[]; // comma-joined on the wire
  destination_region?: string;
  departure_port?: string;
  departure_date_from?: string;
  departure_date_to?: string;
  duration_min?: number;
  duration_max?: number;
  cabin_type?: CabinType;
  max_price_usd?: number;
  page?: number;
  page_size?: number;
}

export async function listSailings(
  params: SailingFilterParams
): Promise<SailingListResponse> {
  const query: Record<string, string | number> = {};
  if (params.cruise_line?.length)
    query.cruise_line = params.cruise_line.join(",");
  if (params.destination_region)
    query.destination_region = params.destination_region;
  if (params.departure_port) query.departure_port = params.departure_port;
  if (params.departure_date_from)
    query.departure_date_from = params.departure_date_from;
  if (params.departure_date_to)
    query.departure_date_to = params.departure_date_to;
  if (params.duration_min != null) query.duration_min = params.duration_min;
  if (params.duration_max != null) query.duration_max = params.duration_max;
  if (params.cabin_type) query.cabin_type = params.cabin_type;
  if (params.max_price_usd != null) query.max_price_usd = params.max_price_usd;
  query.page = params.page ?? 1;
  query.page_size = params.page_size ?? 20;

  const { data } = await api.get<SailingListResponse>("/sailings", {
    params: query,
  });
  return data;
}

export async function getSailing(
  id: string
): Promise<SailingDetailResponse> {
  const { data } = await api.get<SailingDetailResponse>(`/sailings/${id}`);
  return data;
}
