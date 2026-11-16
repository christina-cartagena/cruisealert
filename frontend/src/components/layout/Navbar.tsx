import { Link, NavLink } from "react-router-dom";
import { Ship } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { useLogout } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function Navbar() {
  const user = useAuthStore((s) => s.user);
  const logout = useLogout();

  const navItem = (to: string, label: string) => (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          "text-sm font-medium transition-colors hover:text-primary",
          isActive ? "text-foreground" : "text-muted-foreground"
        )
      }
    >
      {label}
    </NavLink>
  );

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur">
      <div className="container flex h-16 items-center justify-between">
        <Link to="/search" className="flex items-center gap-2 font-bold">
          <Ship className="h-5 w-5 text-primary" />
          CruiseAlert
        </Link>

        <nav className="hidden items-center gap-6 md:flex">
          {navItem("/search", "Search")}
          {user && navItem("/alerts", "Alerts")}
          {user && navItem("/account", "Account")}
          {user && navItem("/billing", "Billing")}
        </nav>

        <div className="flex items-center gap-3">
          {user ? (
            <>
              <Badge variant={user.tier === "pro" ? "default" : "secondary"}>
                {user.tier === "pro" ? "Pro" : "Free"}
              </Badge>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => logout.mutate()}
              >
                Log out
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/login">Log in</Link>
              </Button>
              <Button size="sm" asChild>
                <Link to="/register">Sign up</Link>
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
