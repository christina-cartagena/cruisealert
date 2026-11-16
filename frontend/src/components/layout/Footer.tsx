export function Footer() {
  return (
    <footer className="border-t py-6">
      <div className="container flex flex-col items-center justify-between gap-2 text-sm text-muted-foreground sm:flex-row">
        <p>© {new Date().getFullYear()} CruiseAlert. All rights reserved.</p>
        <p>Cruise pricing data is provided for informational purposes only.</p>
      </div>
    </footer>
  );
}
