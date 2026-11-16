import { useMutation } from "@tanstack/react-query";
import { Check, Sparkles } from "lucide-react";
import { createCheckoutSession, createPortalSession } from "@/api/billing";
import type { BillingPlan } from "@/api/types";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/hooks/use-toast";

const PRO_FEATURES = [
  "Unlimited active alerts",
  "Custom price-drop % thresholds",
  "SMS notifications",
  "90-day price history charts",
  "30-minute price polling",
];

export default function Billing() {
  const user = useAuthStore((s) => s.user);
  const isPro = user?.tier === "pro";

  const checkout = useMutation({
    mutationFn: (plan: BillingPlan) => createCheckoutSession(plan),
    onSuccess: (data) => {
      window.location.href = data.url;
    },
    onError: () =>
      toast({ title: "Could not start checkout", variant: "destructive" }),
  });

  const portal = useMutation({
    mutationFn: () => createPortalSession(),
    onSuccess: (data) => {
      window.location.href = data.url;
    },
    onError: () =>
      toast({ title: "Could not open billing portal", variant: "destructive" }),
  });

  return (
    <div className="container max-w-2xl space-y-6 py-6">
      <h1 className="text-2xl font-bold">Billing</h1>

      {isPro ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              CruiseAlert Pro <Badge>Active</Badge>
            </CardTitle>
            <CardDescription>
              You're on the Pro plan. Manage your subscription, payment method,
              and invoices in the Stripe billing portal.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={() => portal.mutate()}
              disabled={portal.isPending}
            >
              {portal.isPending ? "Opening…" : "Manage subscription"}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-primary">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" /> Upgrade to Pro
            </CardTitle>
            <CardDescription>
              Unlock unlimited alerts and the full price history.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2">
              {PRO_FEATURES.map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm">
                  <Check className="h-4 w-4 text-green-600" /> {f}
                </li>
              ))}
            </ul>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button
                className="flex-1"
                onClick={() => checkout.mutate("monthly")}
                disabled={checkout.isPending}
              >
                Monthly — $9/mo
              </Button>
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => checkout.mutate("annual")}
                disabled={checkout.isPending}
              >
                Annual — $90/yr
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
