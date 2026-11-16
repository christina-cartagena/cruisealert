import { useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { Anchor, ArrowLeft, BellPlus, ExternalLink } from "lucide-react";
import { getSailing } from "@/api/sailings";
import { getPreferences } from "@/api/notifications";
import type { CabinType } from "@/api/types";
import { useAuthStore } from "@/store/auth";
import { PriceChart } from "@/components/sailing/PriceChart";
import { AlertDrawer } from "@/components/alerts/AlertDrawer";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { CABIN_LABELS, CRUISE_LINE_LABELS } from "@/lib/constants";
import { formatPrice, cn } from "@/lib/utils";

function safe(iso: string) {
  try {
    return format(parseISO(iso), "MMM d, yyyy");
  } catch {
    return iso;
  }
}

export default function SailingDetail() {
  const { id = "" } = useParams();
  const user = useAuthStore((s) => s.user);
  const isPro = user?.tier === "pro";

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeCabin, setActiveCabin] = useState<CabinType | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["sailing", id],
    queryFn: () => getSailing(id),
    enabled: !!id,
  });

  // Notification prefs drive the AlertDrawer channel gating.
  const { data: prefs } = useQuery({
    queryKey: ["notification-preferences"],
    queryFn: getPreferences,
    enabled: !!user,
  });

  const cabins = data?.cabins ?? [];
  const selectedCabin = useMemo(() => {
    if (!cabins.length) return null;
    const found = cabins.find((c) => c.cabin_type === activeCabin);
    return found ?? cabins[0];
  }, [cabins, activeCabin]);

  if (isLoading)
    return (
      <div className="container py-6">
        <div className="h-72 w-full animate-pulse rounded-lg bg-muted" />
      </div>
    );

  if (isError || !data)
    return (
      <div className="container py-10 text-center text-muted-foreground">
        Could not load this sailing.{" "}
        <Link to="/search" className="text-primary hover:underline">
          Back to search
        </Link>
      </div>
    );

  return (
    <div className="container py-6">
      <Button variant="ghost" size="sm" asChild className="mb-4">
        <Link to="/search">
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to search
        </Link>
      </Button>

      {/* Hero */}
      <div className="relative mb-6 aspect-[21/9] w-full overflow-hidden rounded-lg bg-muted">
        {data.ship_image_url ? (
          <img
            src={data.ship_image_url}
            alt={data.ship_name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-muted-foreground">
            <Anchor className="h-16 w-16" />
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <div>
            <Badge variant="secondary" className="mb-2">
              {CRUISE_LINE_LABELS[data.cruise_line] ?? data.cruise_line}
            </Badge>
            <h1 className="text-3xl font-bold">{data.ship_name}</h1>
            <p className="text-muted-foreground">
              {data.destination_region} · {data.duration_nights} nights ·
              departs {safe(data.departure_date)} from {data.departure_port}
            </p>
          </div>

          {data.itinerary_ports.length > 0 && (
            <div>
              <h2 className="mb-1 font-semibold">Itinerary</h2>
              <p className="text-sm text-muted-foreground">
                {data.itinerary_ports.join(" → ")}
              </p>
            </div>
          )}

          {/* Cabin tabs */}
          <div>
            <div className="mb-4 flex flex-wrap gap-2 border-b">
              {cabins.map((c) => (
                <button
                  key={c.cabin_type}
                  onClick={() => setActiveCabin(c.cabin_type)}
                  className={cn(
                    "-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                    selectedCabin?.cabin_type === c.cabin_type
                      ? "border-primary text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  )}
                >
                  {CABIN_LABELS[c.cabin_type]}
                </button>
              ))}
            </div>

            {selectedCabin && (
              <div className="space-y-4">
                <div className="flex items-baseline gap-3">
                  <span className="text-2xl font-bold">
                    {formatPrice(selectedCabin.current_price_usd)}
                  </span>
                  {selectedCabin.cabins_available != null && (
                    <span className="text-sm text-muted-foreground">
                      {selectedCabin.cabins_available} cabins available
                    </span>
                  )}
                </div>
                <PriceChart history={selectedCabin.history} isPro={!!isPro} />
              </div>
            )}
          </div>
        </div>

        {/* Sidebar actions */}
        <div className="space-y-4">
          <Card>
            <CardContent className="space-y-3 p-4">
              <Button
                className="w-full"
                onClick={() => {
                  setActiveCabin(selectedCabin?.cabin_type ?? null);
                  setDrawerOpen(true);
                }}
                disabled={!user}
              >
                <BellPlus className="mr-2 h-4 w-4" /> Set alert
              </Button>
              {!user && (
                <p className="text-center text-xs text-muted-foreground">
                  <Link to="/login" className="text-primary hover:underline">
                    Log in
                  </Link>{" "}
                  to set alerts.
                </p>
              )}
              {data.booking_url && (
                <Button variant="outline" className="w-full" asChild>
                  <a
                    href={data.booking_url}
                    target="_blank"
                    rel="noreferrer noopener"
                  >
                    Book now <ExternalLink className="ml-2 h-4 w-4" />
                  </a>
                </Button>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {user && (
        <AlertDrawer
          open={drawerOpen}
          onOpenChange={setDrawerOpen}
          sailingId={data.id}
          shipName={data.ship_name}
          initialCabinType={selectedCabin?.cabin_type}
          tier={user.tier}
          emailVerified={prefs?.email_enabled ?? true}
          phoneVerified={prefs?.phone_verified ?? false}
        />
      )}
    </div>
  );
}
