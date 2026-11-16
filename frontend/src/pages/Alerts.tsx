import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import {
  listAlerts,
  updateAlert,
  deleteAlert,
  deleteAlerts,
} from "@/api/alerts";
import type { Alert } from "@/api/types";
import { AlertsTable } from "@/components/alerts/AlertsTable";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "@/hooks/use-toast";

export default function Alerts() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  // Pending deletion target: a single alert, or the bulk selection.
  const [confirmTarget, setConfirmTarget] = useState<
    { kind: "single"; alert: Alert } | { kind: "bulk" } | null
  >(null);

  const { data: alerts = [], isLoading } = useQuery({
    queryKey: ["alerts"],
    queryFn: listAlerts,
  });

  const toggleStatus = useMutation({
    mutationFn: (a: Alert) =>
      updateAlert(a.id, {
        status: a.status === "active" ? "paused" : "active",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
    onError: () =>
      toast({ title: "Could not update alert", variant: "destructive" }),
  });

  const removeOne = useMutation({
    mutationFn: (id: string) => deleteAlert(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts"] });
      toast({ title: "Alert deleted" });
    },
    onError: () =>
      toast({ title: "Could not delete alert", variant: "destructive" }),
  });

  const removeMany = useMutation({
    mutationFn: (ids: string[]) => deleteAlerts(ids),
    onSuccess: (_d, ids) => {
      qc.invalidateQueries({ queryKey: ["alerts"] });
      setSelected(new Set());
      toast({ title: `${ids.length} alert(s) deleted` });
    },
    onError: () =>
      toast({ title: "Could not delete alerts", variant: "destructive" }),
  });

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const toggleAll = (checked: boolean) =>
    setSelected(checked ? new Set(alerts.map((a) => a.id)) : new Set());

  const confirmDelete = () => {
    if (!confirmTarget) return;
    if (confirmTarget.kind === "single") {
      removeOne.mutate(confirmTarget.alert.id);
    } else {
      removeMany.mutate(Array.from(selected));
    }
    setConfirmTarget(null);
  };

  return (
    <div className="container py-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Your alerts</h1>
        {selected.size > 0 && (
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setConfirmTarget({ kind: "bulk" })}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete selected ({selected.size})
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="h-64 w-full animate-pulse rounded-lg bg-muted" />
      ) : (
        <div className="rounded-lg border">
          <AlertsTable
            alerts={alerts}
            selected={selected}
            onToggle={toggle}
            onToggleAll={toggleAll}
            onTogglePause={(a) => toggleStatus.mutate(a)}
            onDelete={(a) => setConfirmTarget({ kind: "single", alert: a })}
          />
        </div>
      )}

      <Dialog
        open={confirmTarget !== null}
        onOpenChange={(o) => !o && setConfirmTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete alert?</DialogTitle>
            <DialogDescription>
              {confirmTarget?.kind === "bulk"
                ? `This will permanently delete ${selected.size} alert(s). This cannot be undone.`
                : `This will permanently delete the alert for ${
                    confirmTarget?.kind === "single"
                      ? confirmTarget.alert.ship_name
                      : ""
                  }. This cannot be undone.`}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setConfirmTarget(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
