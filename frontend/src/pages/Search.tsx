import { useMemo, useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { SlidersHorizontal } from "lucide-react";
import { listSailings } from "@/api/sailings";
import {
  SailingFilters,
  EMPTY_FILTERS,
  filterStateToParams,
  type FilterState,
} from "@/components/sailing/SailingFilters";
import { SailingCard } from "@/components/sailing/SailingCard";
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { useDebounce } from "@/hooks/useDebounce";

const PAGE_SIZE = 20;

export default function Search() {
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
  const debounced = useDebounce(filters, 400);

  const params = useMemo(() => filterStateToParams(debounced), [debounced]);

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
  } = useInfiniteQuery({
    queryKey: ["sailings", params],
    queryFn: ({ pageParam }) =>
      listSailings({ ...params, page: pageParam, page_size: PAGE_SIZE }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) =>
      lastPage.page < lastPage.pages ? lastPage.page + 1 : undefined,
  });

  const items = data?.pages.flatMap((p) => p.items) ?? [];
  const total = data?.pages[0]?.total ?? 0;

  return (
    <div className="container py-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Find your cruise</h1>
          {!isLoading && (
            <p className="text-sm text-muted-foreground">
              {total.toLocaleString()} sailings
            </p>
          )}
        </div>

        {/* Mobile filter trigger (bottom sheet) */}
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="outline" size="sm" className="md:hidden">
              <SlidersHorizontal className="mr-2 h-4 w-4" /> Filters
            </Button>
          </SheetTrigger>
          <SheetContent side="bottom" className="max-h-[85vh]">
            <SheetHeader className="mb-4">
              <SheetTitle>Filters</SheetTitle>
            </SheetHeader>
            <SailingFilters value={filters} onChange={setFilters} />
          </SheetContent>
        </Sheet>
      </div>

      <div className="flex gap-6">
        <Sidebar>
          <SailingFilters value={filters} onChange={setFilters} />
        </Sidebar>

        <div className="flex-1">
          {isLoading && (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="h-72 animate-pulse rounded-lg bg-muted"
                />
              ))}
            </div>
          )}

          {isError && (
            <div className="rounded-lg border p-8 text-center text-muted-foreground">
              Something went wrong loading sailings. Please try again.
            </div>
          )}

          {!isLoading && !isError && items.length === 0 && (
            <div className="rounded-lg border p-8 text-center text-muted-foreground">
              No sailings match your filters. Try widening your search.
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {items.map((s) => (
              <SailingCard key={s.id} sailing={s} />
            ))}
          </div>

          {hasNextPage && (
            <div className="mt-6 flex justify-center">
              <Button
                variant="outline"
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? "Loading…" : "Load more"}
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
