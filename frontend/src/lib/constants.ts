import type { CruiseLine, CabinType, TriggerType } from "@/api/types";

export const CRUISE_LINES: { value: CruiseLine; label: string }[] = [
  { value: "royal_caribbean", label: "Royal Caribbean" },
  { value: "carnival", label: "Carnival" },
  { value: "norwegian", label: "Norwegian" },
  { value: "celebrity", label: "Celebrity" },
  { value: "princess", label: "Princess" },
  { value: "msc", label: "MSC" },
  { value: "holland_america", label: "Holland America" },
  { value: "disney", label: "Disney" },
  { value: "virgin_voyages", label: "Virgin Voyages" },
];

export const CRUISE_LINE_LABELS: Record<CruiseLine, string> =
  CRUISE_LINES.reduce(
    (acc, l) => ({ ...acc, [l.value]: l.label }),
    {} as Record<CruiseLine, string>
  );

export const CABIN_TYPES: { value: CabinType; label: string }[] = [
  { value: "interior", label: "Interior" },
  { value: "oceanview", label: "Oceanview" },
  { value: "balcony", label: "Balcony" },
  { value: "suite", label: "Suite" },
];

export const CABIN_LABELS: Record<CabinType, string> = CABIN_TYPES.reduce(
  (acc, c) => ({ ...acc, [c.value]: c.label }),
  {} as Record<CabinType, string>
);

export const TRIGGER_TYPES: { value: TriggerType; label: string; help: string }[] =
  [
    {
      value: "price_drop",
      label: "Price drop",
      help: "Notify me when the price falls.",
    },
    {
      value: "back_in_stock",
      label: "Back in stock",
      help: "Notify me when a sold-out cabin becomes available again.",
    },
    {
      value: "availability_threshold",
      label: "Availability warning",
      help: "Notify me when cabins remaining drops to or below a count.",
    },
  ];

export const PRO_MONTHLY_PRICE = 9; // $/mo, used in upsell copy
