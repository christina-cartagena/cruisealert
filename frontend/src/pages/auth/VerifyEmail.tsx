import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, MailCheck, XCircle } from "lucide-react";
import { verifyEmail } from "@/api/auth";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [status, setStatus] = useState<"idle" | "ok" | "error">("idle");

  const verify = useMutation({
    mutationFn: (t: string) => verifyEmail(t),
    onSuccess: () => setStatus("ok"),
    onError: () => setStatus("error"),
  });

  useEffect(() => {
    if (token) verify.mutate(token);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="container flex min-h-[80vh] items-center justify-center">
      <Card className="w-full max-w-sm text-center">
        <CardHeader className="items-center">
          {!token && <MailCheck className="h-12 w-12 text-primary" />}
          {token && status === "ok" && (
            <CheckCircle2 className="h-12 w-12 text-green-600" />
          )}
          {token && status === "error" && (
            <XCircle className="h-12 w-12 text-destructive" />
          )}
          <CardTitle>
            {!token && "Check your inbox"}
            {token && status === "ok" && "Email verified"}
            {token && status === "error" && "Verification failed"}
            {token && status === "idle" && "Verifying…"}
          </CardTitle>
          <CardDescription>
            {!token &&
              "We sent you a verification link. Click it to activate email alerts."}
            {token &&
              status === "ok" &&
              "Your email is confirmed. You can now receive alerts."}
            {token &&
              status === "error" &&
              "This link is invalid or has expired."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild className="w-full">
            <Link to="/search">Continue to CruiseAlert</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
