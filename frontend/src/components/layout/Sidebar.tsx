import { cn } from "@/lib/utils";

interface SidebarProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * Desktop filter sidebar shell. On mobile the same children are rendered
 * inside a bottom Sheet by the consuming page (see Search.tsx).
 */
export function Sidebar({ children, className }: SidebarProps) {
  return (
    <aside
      className={cn(
        "hidden w-72 shrink-0 border-r pr-6 md:block",
        className
      )}
    >
      <div className="sticky top-20 space-y-6">{children}</div>
    </aside>
  );
}
