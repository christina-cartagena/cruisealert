import { Link } from "react-router-dom";
import { format, parseISO, differenceInCalendarDays } from "date-fns";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PriceHistoryPoint } from "@/api/types";
import { Button } from "@/components/ui/button";
import { formatPrice, cn } from "@/lib/utils";

interface Props {
  history: PriceHistoryPoint[];
  // Free users only get to *see* 7 days clearly; older data is blurred.
  isPro: boolean;
}

interface ChartPoint {
  date: string;
  label: string;
  price: number;
}

function toChartData(history: PriceHistoryPoint[]): ChartPoint[] {
  return [...history]
    .map((p) => ({
      date: p.recorded_at,
      label: safeLabel(p.recorded_at),
      price: parseFloat(p.price_usd),
    }))
    .filter((p) => !Number.isNaN(p.price))
    .sort((a, b) => a.date.localeCompare(b.date));
}

function safeLabel(iso: string) {
  try {
    return format(parseISO(iso), "MMM d");
  } catch {
    return iso;
  }
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload as ChartPoint;
  return (
    <div className="rounded-md border bg-background p-2 text-sm shadow-md">
      <div className="font-medium">{p.label}</div>
      <div className="text-primary">{formatPrice(p.price)}</div>
    </div>
  );
}

export function PriceChart({ history, isPro }: Props) {
  const data = toChartData(history);

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border text-sm text-muted-foreground">
        No price history yet for this cabin.
      </div>
    );
  }

  // For free users, blur the portion of the chart older than 7 days and
  // show an upgrade overlay. We detect whether older-than-7-day data exists.
  const now = new Date();
  const hasOlderData =
    !isPro &&
    data.some((d) => {
      try {
        return differenceInCalendarDays(now, parseISO(d.date)) > 7;
      } catch {
        return false;
      }
    });

  return (
    <div className="relative">
      <div
        className={cn(
          "h-64 w-full transition",
          hasOlderData && "pointer-events-none select-none blur-sm"
        )}
      >
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.4} />
                <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 12 }}
              minTickGap={24}
            />
            <YAxis
              tick={{ fontSize: 12 }}
              width={60}
              tickFormatter={(v) => formatPrice(v)}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="price"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              fill="url(#priceFill)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {hasOlderData && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 rounded-lg bg-background/40 text-center">
          <p className="max-w-xs font-medium">
            See the full 90-day price history with CruiseAlert Pro
          </p>
          <Button asChild>
            <Link to="/billing">Upgrade to Pro</Link>
          </Button>
        </div>
      )}
    </div>
  );
}
