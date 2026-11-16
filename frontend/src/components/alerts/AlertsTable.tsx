import { formatDistanceToNow, parseISO } from "date-fns";
import { Pause, Play, Trash2 } from "lucide-react";
import type { Alert } from "@/api/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { CABIN_LABELS } from "@/lib/constants";

const STATUS_VARIANT = {
  active: "active",
  paused: "paused",
  fired: "fired",
  expired: "expired",
} as const;

const TRIGGER_LABEL: Record<Alert["trigger_type"], string> = {
  price_drop: "Price drop",
  back_in_stock: "Back in stock",
  availability_threshold: "Availability",
};

function describeThreshold(a: Alert): string {
  if (a.trigger_type === "price_drop")
    return a.threshold_pct ? `≥ ${a.threshold_pct}%` : "Any drop";
  if (a.trigger_type === "availability_threshold")
    return `≤ ${a.threshold_count ?? "?"}`;
  return "—";
}

function lastChecked(iso: string | null): string {
  if (!iso) return "Never";
  try {
    return `${formatDistanceToNow(parseISO(iso))} ago`;
  } catch {
    return iso;
  }
}

interface Props {
  alerts: Alert[];
  selected: Set<string>;
  onToggle: (id: string) => void;
  onToggleAll: (checked: boolean) => void;
  onTogglePause: (alert: Alert) => void;
  onDelete: (alert: Alert) => void;
}

export function AlertsTable({
  alerts,
  selected,
  onToggle,
  onToggleAll,
  onTogglePause,
  onDelete,
}: Props) {
  const allChecked = alerts.length > 0 && selected.size === alerts.length;

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-10">
            <Checkbox
              checked={allChecked}
              onCheckedChange={(c) => onToggleAll(Boolean(c))}
              aria-label="Select all"
            />
          </TableHead>
          <TableHead>Sailing</TableHead>
          <TableHead>Ship</TableHead>
          <TableHead>Cabin</TableHead>
          <TableHead>Trigger</TableHead>
          <TableHead>Threshold</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Last Checked</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {alerts.map((a) => (
          <TableRow
            key={a.id}
            data-state={selected.has(a.id) ? "selected" : undefined}
          >
            <TableCell>
              <Checkbox
                checked={selected.has(a.id)}
                onCheckedChange={() => onToggle(a.id)}
                aria-label={`Select ${a.ship_name}`}
              />
            </TableCell>
            <TableCell className="max-w-[160px] truncate">
              {a.destination_region}
            </TableCell>
            <TableCell>{a.ship_name}</TableCell>
            <TableCell>{CABIN_LABELS[a.cabin_type]}</TableCell>
            <TableCell>{TRIGGER_LABEL[a.trigger_type]}</TableCell>
            <TableCell>{describeThreshold(a)}</TableCell>
            <TableCell>
              <Badge variant={STATUS_VARIANT[a.status]}>{a.status}</Badge>
            </TableCell>
            <TableCell className="text-muted-foreground">
              {lastChecked(a.last_checked_at)}
            </TableCell>
            <TableCell className="text-right">
              <div className="flex justify-end gap-1">
                {(a.status === "active" || a.status === "paused") && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onTogglePause(a)}
                    title={a.status === "active" ? "Pause" : "Resume"}
                  >
                    {a.status === "active" ? (
                      <Pause className="h-4 w-4" />
                    ) : (
                      <Play className="h-4 w-4" />
                    )}
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => onDelete(a)}
                  title="Delete"
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
        {alerts.length === 0 && (
          <TableRow>
            <TableCell
              colSpan={9}
              className="py-10 text-center text-muted-foreground"
            >
              You have no alerts yet. Open a sailing and set one.
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}
