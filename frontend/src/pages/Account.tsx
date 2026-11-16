import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2 } from "lucide-react";
import {
  getPreferences,
  updatePreferences,
  sendPhoneVerification,
  checkPhoneVerification,
} from "@/api/notifications";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toast } from "@/hooks/use-toast";

export default function Account() {
  const qc = useQueryClient();
  const user = useAuthStore((s) => s.user);

  const { data: prefs } = useQuery({
    queryKey: ["notification-preferences"],
    queryFn: getPreferences,
  });

  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);

  const sendCode = useMutation({
    mutationFn: () => sendPhoneVerification(phone),
    onSuccess: () => {
      setCodeSent(true);
      toast({ title: "Code sent", description: "Check your phone for an SMS." });
    },
    onError: () =>
      toast({ title: "Could not send code", variant: "destructive" }),
  });

  const checkCode = useMutation({
    mutationFn: () => checkPhoneVerification(phone, code),
    onSuccess: (res) => {
      if (res.verified) {
        qc.invalidateQueries({ queryKey: ["notification-preferences"] });
        toast({ title: "Phone verified" });
        setCodeSent(false);
        setCode("");
      } else {
        toast({ title: "Incorrect code", variant: "destructive" });
      }
    },
    onError: () =>
      toast({ title: "Verification failed", variant: "destructive" }),
  });

  const togglePref = useMutation({
    mutationFn: (patch: { email_enabled?: boolean; sms_enabled?: boolean }) =>
      updatePreferences(patch),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["notification-preferences"] }),
  });

  return (
    <div className="container max-w-2xl space-y-6 py-6">
      <h1 className="text-2xl font-bold">Account</h1>

      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Email</span>
            <span>{user?.email}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Plan</span>
            <Badge variant={user?.tier === "pro" ? "default" : "secondary"}>
              {user?.tier === "pro" ? "Pro" : "Free"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Notification preferences</CardTitle>
          <CardDescription>Choose how we reach you.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <Label>Email alerts</Label>
            <Switch
              checked={prefs?.email_enabled ?? false}
              onCheckedChange={(c) => togglePref.mutate({ email_enabled: c })}
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <Label>SMS alerts</Label>
              {!prefs?.phone_verified && (
                <p className="text-xs text-muted-foreground">
                  Verify a phone number to enable SMS.
                </p>
              )}
            </div>
            <Switch
              checked={prefs?.sms_enabled ?? false}
              disabled={!prefs?.phone_verified}
              onCheckedChange={(c) => togglePref.mutate({ sms_enabled: c })}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Phone number
            {prefs?.phone_verified && (
              <Badge variant="success">
                <CheckCircle2 className="mr-1 h-3 w-3" /> Verified
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            {prefs?.phone_verified
              ? `Verified: ${prefs.phone_e164}`
              : "Add and verify a number to receive SMS alerts."}
          </CardDescription>
        </CardHeader>
        {!prefs?.phone_verified && (
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="phone">Phone (E.164)</Label>
              <div className="flex gap-2">
                <Input
                  id="phone"
                  placeholder="+14155552671"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
                <Button
                  variant="outline"
                  onClick={() => sendCode.mutate()}
                  disabled={!phone || sendCode.isPending}
                >
                  {sendCode.isPending ? "Sending…" : "Send code"}
                </Button>
              </div>
            </div>

            {codeSent && (
              <div className="space-y-2">
                <Label htmlFor="code">Verification code</Label>
                <div className="flex gap-2">
                  <Input
                    id="code"
                    placeholder="123456"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                  />
                  <Button
                    onClick={() => checkCode.mutate()}
                    disabled={!code || checkCode.isPending}
                  >
                    {checkCode.isPending ? "Verifying…" : "Verify"}
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        )}
      </Card>
    </div>
  );
}
