import { Link } from "react-router-dom";
import { format, parseISO } from "date-fns";
import { TrendingDown, TrendingUp, Minus, Anchor } from "lucide-react";
import type { SailingListItem } from "@/api/types";
import { CRUISE_LINE_LABELS, CABIN_LABELS } from "@/lib/constants";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatPrice, cn } from "@/lib/utils";

function TrendIndicator({ trend }: { trend: SailingListItem["price_trend"] }) {
  if (trend === "down")
    return (
      <span className="flex items-center gap-1 text-sm font-medium text-green-600">
        <TrendingDown className="h-4 w-4" /> Dropping
      </span>
    );
  if (trend === "up")
    return (
      <span className="flex items-center gap-1 text-sm font-medium text-red-600">
        <TrendingUp className="h-4 w-4" /> Rising
      </span>
    );
  return (
    <span className="flex items-center gap-1 text-sm font-medium text-muted-foreground">
      <Minus className="h-4 w-4" /> Stable
    </span>
  );
}

function safeDate(iso: string) {
  try {
    return format(parseISO(iso), "MMM d, yyyy");
  } catch {
    return iso;
  }
}

export function SailingCard({ sailing }: { sailing: SailingListItem }) {
  return (
    <Link to={`/sailings/${sailing.id}`} className="block">
      <Card className="h-full overflow-hidden transition-shadow hover:shadow-md">
        <div className="aspect-[16/9] w-full overflow-hidden bg-muted">
          {sailing.ship_image_url ? (
            <img
              src={sailing.ship_image_url}
              alt={sailing.ship_name}
              className="h-full w-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-muted-foreground">
              <Anchor className="h-10 w-10" />
            </div>
          )}
        </div>
        <CardContent className="space-y-2 p-4">
          <div className="flex items-center justify-between">
            <Badge variant="secondary">
              {CRUISE_LINE_LABELS[sailing.cruise_line] ?? sailing.cruise_line}
            </Badge>
            <TrendIndicator trend={sailing.price_trend} />
          </div>
          <h3 className="font-semibold leading-tight">{sailing.ship_name}</h3>
          <p className="text-sm text-muted-foreground">
            {sailing.destination_region} · {sailing.departure_port}
          </p>
          <p className="text-sm text-muted-foreground">
            {safeDate(sailing.departure_date)} · {sailing.duration_nights}{" "}
            nights
          </p>
        </CardContent>
        <CardFooter className="flex items-baseline justify-between p-4 pt-0">
          <div>
            <span className={cn("text-xl font-bold")}>
              {formatPrice(sailing.lowest_price_usd)}
            </span>
            {sailing.lowest_cabin_type && (
              <span className="ml-1 text-xs text-muted-foreground">
                {CABIN_LABELS[sailing.lowest_cabin_type]}
              </span>
            )}
          </div>
        </CardFooter>
      </Card>
    </Link>
  );
}
