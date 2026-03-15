"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ListOrdered,
  Settings,
  Beaker,
  ShieldCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";

const baseNavItems = [
  {
    title: "OVERVIEW",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    title: "QUEUES",
    href: "/dashboard/queues",
    icon: ListOrdered,
  },
  {
    title: "JOBS",
    href: "/dashboard/jobs",
    icon: Beaker,
  },
  {
    title: "SETTINGS",
    href: "/dashboard/settings",
    icon: Settings,
  },
];

const adminNavItem = {
  title: "ADMIN",
  href: "/dashboard/admin",
  icon: ShieldCheck,
};

export function Sidebar({ isAdmin = false }: { isAdmin?: boolean }) {
  const pathname = usePathname();
  const navItems = isAdmin ? [...baseNavItems, adminNavItem] : baseNavItems;

  return (
    <aside className="w-56 bg-black border-r border-[#333] flex flex-col font-mono">
      <div className="p-4 border-b border-[#333]">
        <h1 className="text-lg font-bold text-[#00ff00]">OpenQueue</h1>
        <p className="text-xs text-[#666]">terminal dashboard</p>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        {navItems.map((item) => {
          const isActive =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 text-sm font-medium transition-colors border-l-2",
                isActive
                  ? "border-[#00ff00] bg-[#111] text-white"
                  : "border-transparent text-[#666] hover:text-white hover:bg-[#111]"
              )}
            >
              <item.icon className={cn("h-4 w-4", isActive ? "text-[#00ff00]" : "")} />
              {item.title}
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-[#333]">
        <p className="text-xs text-[#444]">v0.1.0</p>
      </div>
    </aside>
  );
}
