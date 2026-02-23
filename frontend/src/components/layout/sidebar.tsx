"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileSearch,
  Upload,
  Building2,
} from "lucide-react";

const navigation = [
  {
    name: "Observatoire",
    href: "/dashboard",
    icon: LayoutDashboard,
    description: "Vue globale & KPIs",
  },
  {
    name: "Analyse",
    href: "/analysis",
    icon: FileSearch,
    description: "Analyse documentaire",
  },
  {
    name: "Administration",
    href: "/admin/ingest",
    icon: Upload,
    description: "Ingestion des données",
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-64 flex-shrink-0 bg-[var(--color-ceser-blue)] lg:flex lg:flex-col">
      <div className="flex h-16 items-center gap-3 border-b border-white/10 px-6">
        <Building2 className="h-7 w-7 text-white" />
        <div>
          <h1 className="text-sm font-semibold leading-tight text-white">
            Signaux Faibles
          </h1>
          <p className="text-[10px] font-medium uppercase tracking-wider text-white/60">
            CESER de France
          </p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const isActive =
            pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                isActive
                  ? "bg-white/15 text-white"
                  : "text-white/70 hover:bg-white/10 hover:text-white"
              }`}
            >
              <item.icon className="h-5 w-5 flex-shrink-0" />
              <div>
                <div className="font-medium">{item.name}</div>
                <div
                  className={`text-[11px] ${
                    isActive ? "text-white/60" : "text-white/40"
                  }`}
                >
                  {item.description}
                </div>
              </div>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-white/10 px-6 py-4">
        <p className="text-[10px] text-white/40">
          Hackathon GAIA 2026
        </p>
        <p className="text-[10px] text-white/30">v0.1.0 — MVP</p>
      </div>
    </aside>
  );
}
