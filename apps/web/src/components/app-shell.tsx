"use client";

import { ReactNode, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  Droplets,
  Home,
  LogOut,
  type LucideIcon,
  Menu,
  Settings,
  Sprout,
  TreeDeciduous,
  TreePine,
  Users,
  Waves,
} from "lucide-react";

import { useSensors } from "@/api/sensors";
import { useLogout, useSession } from "@/api/auth";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  /** Shown only to these roles; the API refuses the others anyway (RBAC). */
  roles?: readonly string[];
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Home", icon: Home },
  { href: "/farms", label: "Farms", icon: Sprout },
  { href: "/zones", label: "Zones", icon: TreePine },
  { href: "/trees", label: "Trees", icon: TreeDeciduous },
  { href: "/sensors", label: "Sensors", icon: Activity },
  { href: "/water-sources", label: "Water sources", icon: Droplets },
  { href: "/water-switchers", label: "Water switchers", icon: Waves },
  { href: "/irrigation-tasks", label: "Irrigation tasks", icon: Activity },
  { href: "/users", label: "Users", icon: Users, roles: ["admin", "owner"] },
];

function BrandLockup({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <Image
        src="/brand/tilthwave-mark.svg"
        alt="tilthwave"
        width={28}
        height={28}
        priority
      />
      <div className="flex items-baseline gap-2 leading-none">
        <span className="font-heading text-base font-semibold tracking-tight text-foreground">
          tilthwave
        </span>
        <span className="hidden text-muted-foreground/70 sm:inline">·</span>
        <span className="hidden text-xs text-muted-foreground sm:inline">
          farm watch
        </span>
      </div>
    </div>
  );
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const role = useSession().data?.role;
  const items = NAV_ITEMS.filter((item) => !item.roles || (role !== undefined && item.roles.includes(role)));
  return (
    <nav className="flex flex-col gap-0.5 p-2">
      {items.map(({ href, label, icon: Icon }) => {
        const active =
          href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
              active
                ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
            )}
          >
            <Icon className="size-4" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

function LiveSensorsBadge() {
  const { data, isPending } = useSensors({ size: 1 });
  const total = data?.total ?? 0;

  return (
    <div className="flex items-center gap-2 rounded-full border border-border/60 bg-card px-3 py-1 text-xs font-medium text-foreground">
      <span className="relative flex size-2">
        <span className="tilthwave-pulse-dot absolute inline-flex size-full rounded-full bg-pulse" />
        <span className="relative inline-flex size-2 rounded-full bg-field" />
      </span>
      <span>
        {isPending ? "—" : total} sensor{total === 1 ? "" : "s"} live
      </span>
    </div>
  );
}

function UserMenu() {
  const router = useRouter();
  const logoutMutation = useLogout();
  const { data: session } = useSession();

  async function handleLogout() {
    try {
      await logoutMutation.mutateAsync(); // POST /auth/logout clears the httpOnly cookie
    } finally {
      router.replace("/login");
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button variant="ghost" size="icon" aria-label="User menu">
            <Users />
          </Button>
        }
      />
      <DropdownMenuContent align="end" className="min-w-52">
        {session ? (
          // DropdownMenuLabel is base-ui's Menu.GroupLabel: it reads its Group's context and
          // throws when rendered outside one, which took the whole page to the error boundary
          // the first time this menu opened. It must sit inside a DropdownMenuGroup.
          <DropdownMenuGroup>
            <DropdownMenuLabel className="grid gap-0.5 font-normal">
              <span className="font-medium text-foreground">{session.username}</span>
              <span className="text-xs text-muted-foreground">
                <span className="capitalize">{session.role}</span>
                {session.farm_name ? ` · ${session.farm_name}` : ""}
              </span>
            </DropdownMenuLabel>
          </DropdownMenuGroup>
        ) : null}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => router.push("/settings")}>
          <Settings /> Settings
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleLogout}>
          <LogOut /> Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex flex-1 min-h-full">
      <aside className="hidden w-64 shrink-0 border-r border-border bg-sidebar md:flex md:flex-col">
        <div className="flex h-16 items-center border-b border-border px-4">
          <BrandLockup />
        </div>
        <NavLinks />
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex h-16 items-center justify-between gap-3 border-b border-border bg-background px-4">
          <div className="flex items-center gap-2">
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger
                render={
                  <Button
                    variant="ghost"
                    size="icon"
                    className="md:hidden"
                    aria-label="Open menu"
                  >
                    <Menu />
                  </Button>
                }
              />
              <SheetContent side="left" className="p-0">
                <SheetHeader>
                  <SheetTitle className="sr-only">
                    tilthwave
                  </SheetTitle>
                  <BrandLockup />
                </SheetHeader>
                <NavLinks onNavigate={() => setMobileOpen(false)} />
              </SheetContent>
            </Sheet>
            <div className="md:hidden">
              <BrandLockup />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <LiveSensorsBadge />
            <UserMenu />
          </div>
        </header>
        <main className="flex flex-1 flex-col p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}