import { format, parseISO } from "date-fns";
import type { Alert } from "@/api/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CABIN_LABELS, CRUISE_LINE_LABELS } from "@/lib/constants";

const STATUS_VARIANT = {
  active: "active",
  paused: "paused",
  fired: "fired",
  expired: "expired",
} as const;

const TRIGGER_LABEL: Record<Alert["trigger_type"], string> = {
  price_drop: "Price drop",
  back_in_stock: "Back in stock",
  availability_threshold: "Availability warning",
};

function describeThreshold(a: Alert): string {
  if (a.trigger_type === "price_drop")
    return a.threshold_pct ? `≥ ${a.threshold_pct}% drop` : "Any drop";
  if (a.trigger_type === "availability_threshold")
    return `≤ ${a.threshold_count ?? "?"} cabins left`;
  return "—";
}

export function AlertCard({ alert }: { alert: Alert }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 p-4">
        <div>
          <CardTitle className="text-base">{alert.ship_name}</CardTitle>
          <p className="text-sm text-muted-foreground">
            {CRUISE_LINE_LABELS[alert.cruise_line] ?? alert.cruise_line} ·{" "}
            {CABIN_LABELS[alert.cabin_type]}
          </p>
        </div>
        <Badge variant={STATUS_VARIANT[alert.status]}>{alert.status}</Badge>
      </CardHeader>
      <CardContent className="space-y-1 p-4 pt-0 text-sm">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Trigger</span>
          <span>{TRIGGER_LABEL[alert.trigger_type]}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Threshold</span>
          <span>{describeThreshold(alert)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Departs</span>
          <span>{safe(alert.departure_date)}</span>
        </div>
      </CardContent>
    </Card>
  );
}

function safe(iso: string) {
  try {
    return format(parseISO(iso), "MMM d, yyyy");
  } catch {
    return iso;
  }
}
