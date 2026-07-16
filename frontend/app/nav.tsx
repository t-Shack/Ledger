import Link from "next/link";

const LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/upload", label: "Upload" },
  { href: "/review", label: "Review" },
  { href: "/settings", label: "Settings" },
];

export function Nav() {
  return (
    <nav className="border-b border-border">
      <div className="mx-auto flex max-w-2xl items-center justify-between px-6 py-4">
        <span className="font-display text-sm font-medium text-text-primary">Budget Tracker</span>
        <div className="flex gap-5">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-sm text-text-secondary transition hover:text-text-primary"
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
