import type { SailingFilterParams } from "@/api/sailings";
import type { CruiseLine, CabinType } from "@/api/types";
import { CRUISE_LINES, CABIN_TYPES } from "@/lib/constants";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export interface FilterState {
  cruise_line: CruiseLine[];
  destination_region: string;
  departure_port: string;
  departure_date_from: string;
  departure_date_to: string;
  duration_min: string;
  duration_max: string;
  cabin_type: CabinType | "any";
  max_price_usd: string;
}

export const EMPTY_FILTERS: FilterState = {
  cruise_line: [],
  destination_region: "",
  departure_port: "",
  departure_date_from: "",
  departure_date_to: "",
  duration_min: "",
  duration_max: "",
  cabin_type: "any",
  max_price_usd: "",
};

export function filterStateToParams(
  f: FilterState
): Omit<SailingFilterParams, "page" | "page_size"> {
  return {
    cruise_line: f.cruise_line.length ? f.cruise_line : undefined,
    destination_region: f.destination_region.trim() || undefined,
    departure_port: f.departure_port.trim() || undefined,
    departure_date_from: f.departure_date_from || undefined,
    departure_date_to: f.departure_date_to || undefined,
    duration_min: f.duration_min ? Number(f.duration_min) : undefined,
    duration_max: f.duration_max ? Number(f.duration_max) : undefined,
    cabin_type: f.cabin_type === "any" ? undefined : f.cabin_type,
    max_price_usd: f.max_price_usd ? Number(f.max_price_usd) : undefined,
  };
}

interface Props {
  value: FilterState;
  onChange: (next: FilterState) => void;
}

export function SailingFilters({ value, onChange }: Props) {
  const set = <K extends keyof FilterState>(key: K, v: FilterState[K]) =>
    onChange({ ...value, [key]: v });

  const toggleLine = (line: CruiseLine) => {
    const exists = value.cruise_line.includes(line);
    set(
      "cruise_line",
      exists
        ? value.cruise_line.filter((l) => l !== line)
        : [...value.cruise_line, line]
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Filters</h2>
        <Button
          variant="link"
          size="sm"
          className="h-auto p-0"
          onClick={() => onChange(EMPTY_FILTERS)}
        >
          Clear all
        </Button>
      </div>

      <div className="space-y-2">
        <Label>Cruise line</Label>
        <div className="space-y-2">
          {CRUISE_LINES.map((l) => (
            <label
              key={l.value}
              className="flex cursor-pointer items-center gap-2 text-sm"
            >
              <Checkbox
                checked={value.cruise_line.includes(l.value)}
                onCheckedChange={() => toggleLine(l.value)}
              />
              {l.label}
            </label>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="destination">Destination</Label>
        <Input
          id="destination"
          placeholder="Caribbean, Alaska…"
          value={value.destination_region}
          onChange={(e) => set("destination_region", e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="port">Departure port</Label>
        <Input
          id="port"
          placeholder="Miami, FL"
          value={value.departure_port}
          onChange={(e) => set("departure_port", e.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-2">
          <Label htmlFor="from">Depart from</Label>
          <Input
            id="from"
            type="date"
            value={value.departure_date_from}
            onChange={(e) => set("departure_date_from", e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="to">Depart to</Label>
          <Input
            id="to"
            type="date"
            value={value.departure_date_to}
            onChange={(e) => set("departure_date_to", e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-2">
          <Label htmlFor="dmin">Min nights</Label>
          <Input
            id="dmin"
            type="number"
            min={1}
            value={value.duration_min}
            onChange={(e) => set("duration_min", e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="dmax">Max nights</Label>
          <Input
            id="dmax"
            type="number"
            min={1}
            value={value.duration_max}
            onChange={(e) => set("duration_max", e.target.value)}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label>Cabin type</Label>
        <Select
          value={value.cabin_type}
          onValueChange={(v) => set("cabin_type", v as FilterState["cabin_type"])}
        >
          <SelectTrigger>
            <SelectValue placeholder="Any cabin" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="any">Any cabin</SelectItem>
            {CABIN_TYPES.map((c) => (
              <SelectItem key={c.value} value={c.value}>
                {c.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="maxprice">Max price (USD)</Label>
        <Input
          id="maxprice"
          type="number"
          min={0}
          placeholder="2000"
          value={value.max_price_usd}
          onChange={(e) => set("max_price_usd", e.target.value)}
        />
      </div>
    </div>
  );
}
