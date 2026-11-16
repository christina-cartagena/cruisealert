import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { Sparkles } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { createAlert } from "@/api/alerts";
import type {
  CabinType,
  TriggerType,
  CreateAlertPayload,
  Tier,
} from "@/api/types";
import { CABIN_TYPES, TRIGGER_TYPES, PRO_MONTHLY_PRICE } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sailingId: string;
  shipName: string;
  // Cabin pre-selected from the detail tab, if any.
  initialCabinType?: CabinType;
  tier: Tier;
  emailVerified: boolean;
  phoneVerified: boolean;
}

type Step = 1 | 2 | 3 | 4;

export function AlertDrawer({
  open,
  onOpenChange,
  sailingId,
  shipName,
  initialCabinType,
  tier,
  emailVerified,
  phoneVerified,
}: Props) {
  const isPro = tier === "pro";
  const qc = useQueryClient();

  const [step, setStep] = useState<Step>(initialCabinType ? 2 : 1);
  const [cabinType, setCabinType] = useState<CabinType | undefined>(
    initialCabinType
  );
  const [triggerType, setTriggerType] = useState<TriggerType>("price_drop");
  const [thresholdPct, setThresholdPct] = useState<string>("");
  const [thresholdCount, setThresholdCount] = useState<string>("");
  const [emailEnabled, setEmailEnabled] = useState<boolean>(true);
  const [smsEnabled, setSmsEnabled] = useState<boolean>(false);
  const [showUpsell, setShowUpsell] = useState(false);

  // Reset internal state whenever the drawer (re)opens.
  useEffect(() => {
    if (open) {
      setStep(initialCabinType ? 2 : 1);
      setCabinType(initialCabinType);
      setTriggerType("price_drop");
      setThresholdPct("");
      setThresholdCount("");
      setEmailEnabled(emailVerified);
      setSmsEnabled(false);
      setShowUpsell(false);
    }
  }, [open, initialCabinType, emailVerified]);

  const mutation = useMutation({
    mutationFn: (payload: CreateAlertPayload) => createAlert(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts"] });
      toast({
        title: "Alert created",
        description: `We'll watch ${shipName} and let you know.`,
      });
      onOpenChange(false);
    },
    onError: (err) => {
      // On a free-tier 403 alert_limit_reached, show upsell INSTEAD of closing.
      if (
        isAxiosError(err) &&
        err.response?.status === 403 &&
        err.response.data?.code === "alert_limit_reached"
      ) {
        setShowUpsell(true);
        return;
      }
      toast({
        title: "Could not create alert",
        description: "Something went wrong. Please try again.",
        variant: "destructive",
      });
    },
  });

  const submit = () => {
    if (!cabinType) {
      setStep(1);
      return;
    }
    const payload: CreateAlertPayload = {
      sailing_id: sailingId,
      cabin_type: cabinType,
      trigger_type: triggerType,
      threshold_pct:
        triggerType === "price_drop" && isPro && thresholdPct !== ""
          ? Number(thresholdPct)
          : null,
      threshold_count:
        triggerType === "availability_threshold" && thresholdCount !== ""
          ? Number(thresholdCount)
          : null,
      email_enabled: emailEnabled,
      sms_enabled: smsEnabled && phoneVerified,
    };
    mutation.mutate(payload);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full flex-col sm:max-w-md">
        {showUpsell ? (
          <UpsellScreen onClose={() => onOpenChange(false)} />
        ) : (
          <>
            <SheetHeader>
              <SheetTitle>Set a price alert</SheetTitle>
              <SheetDescription>{shipName}</SheetDescription>
            </SheetHeader>

            <StepIndicator current={step} />

            <div className="flex-1 space-y-6 py-4">
              {step === 1 && (
                <div className="space-y-3">
                  <Label>Cabin type</Label>
                  <div className="grid grid-cols-2 gap-2">
                    {CABIN_TYPES.map((c) => (
                      <Button
                        key={c.value}
                        variant={cabinType === c.value ? "default" : "outline"}
                        onClick={() => setCabinType(c.value)}
                      >
                        {c.label}
                      </Button>
                    ))}
                  </div>
                </div>
              )}

              {step === 2 && (
                <div className="space-y-3">
                  <Label>What should we watch for?</Label>
                  <div className="space-y-2">
                    {TRIGGER_TYPES.map((t) => (
                      <label
                        key={t.value}
                        className={cn(
                          "flex cursor-pointer flex-col rounded-md border p-3",
                          triggerType === t.value &&
                            "border-primary ring-1 ring-primary"
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <input
                            type="radio"
                            name="trigger"
                            checked={triggerType === t.value}
                            onChange={() => setTriggerType(t.value)}
                          />
                          <span className="font-medium">{t.label}</span>
                        </div>
                        <span className="ml-6 text-sm text-muted-foreground">
                          {t.help}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {step === 3 && (
                <div className="space-y-4">
                  {triggerType === "price_drop" && (
                    <div className="space-y-2">
                      <Label htmlFor="pct">Minimum drop (%)</Label>
                      {isPro ? (
                        <Input
                          id="pct"
                          type="number"
                          min={0}
                          max={100}
                          placeholder="Any drop"
                          value={thresholdPct}
                          onChange={(e) => setThresholdPct(e.target.value)}
                        />
                      ) : (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <div>
                                <Input
                                  id="pct"
                                  type="number"
                                  placeholder="Any drop"
                                  disabled
                                />
                              </div>
                            </TooltipTrigger>
                            <TooltipContent>Upgrade to Pro</TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      )}
                      <p className="text-xs text-muted-foreground">
                        {isPro
                          ? "Leave blank to be alerted on any drop."
                          : "Free alerts fire on any drop. Set a custom % with Pro."}
                      </p>
                    </div>
                  )}

                  {triggerType === "availability_threshold" && (
                    <div className="space-y-2">
                      <Label htmlFor="count">Alert when cabins left ≤</Label>
                      <Input
                        id="count"
                        type="number"
                        min={0}
                        placeholder="5"
                        value={thresholdCount}
                        onChange={(e) => setThresholdCount(e.target.value)}
                      />
                    </div>
                  )}

                  {triggerType === "back_in_stock" && (
                    <p className="text-sm text-muted-foreground">
                      We'll notify you the moment this cabin becomes available
                      again. No threshold needed.
                    </p>
                  )}
                </div>
              )}

              {step === 4 && (
                <div className="space-y-4">
                  <Label>Notification channels</Label>
                  <div className="flex items-center justify-between rounded-md border p-3">
                    <div>
                      <p className="font-medium">Email</p>
                      <p className="text-sm text-muted-foreground">
                        {emailVerified
                          ? "Sent to your verified email."
                          : "Verify your email to enable."}
                      </p>
                    </div>
                    <Switch
                      checked={emailEnabled}
                      disabled={!emailVerified}
                      onCheckedChange={setEmailEnabled}
                    />
                  </div>

                  <div className="flex items-center justify-between rounded-md border p-3">
                    <div>
                      <p className="font-medium">SMS</p>
                      {phoneVerified ? (
                        <p className="text-sm text-muted-foreground">
                          Sent to your verified number.
                        </p>
                      ) : (
                        <Link
                          to="/account"
                          className="text-sm text-primary underline-offset-4 hover:underline"
                        >
                          Verify number
                        </Link>
                      )}
                    </div>
                    <Switch
                      checked={smsEnabled}
                      disabled={!phoneVerified}
                      onCheckedChange={setSmsEnabled}
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between gap-2 border-t pt-4">
              <Button
                variant="ghost"
                onClick={() => setStep((s) => (Math.max(1, s - 1) as Step))}
                disabled={step === 1}
              >
                Back
              </Button>
              {step < 4 ? (
                <Button
                  onClick={() => setStep((s) => (Math.min(4, s + 1) as Step))}
                  disabled={step === 1 && !cabinType}
                >
                  Next
                </Button>
              ) : (
                <Button
                  onClick={submit}
                  disabled={mutation.isPending || (!emailEnabled && !smsEnabled)}
                >
                  {mutation.isPending ? "Creating…" : "Create alert"}
                </Button>
              )}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

function StepIndicator({ current }: { current: Step }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4].map((n) => (
        <div
          key={n}
          className={cn(
            "h-1 flex-1 rounded-full",
            n <= current ? "bg-primary" : "bg-muted"
          )}
        />
      ))}
    </div>
  );
}

function UpsellScreen({ onClose }: { onClose: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
      <Sparkles className="h-10 w-10 text-primary" />
      <SheetTitle>You've hit the free limit</SheetTitle>
      <p className="max-w-xs text-muted-foreground">
        Free tier limit is 3 active alerts. Upgrade to Pro for unlimited
        alerts, custom price-drop thresholds, SMS notifications, and 90-day
        price history.
      </p>
      <Button asChild size="lg">
        <Link to="/billing">Upgrade to Pro — ${PRO_MONTHLY_PRICE}/mo</Link>
      </Button>
      <Button variant="ghost" onClick={onClose}>
        Maybe later
      </Button>
    </div>
  );
}
