"use client";

import { usePathname } from "next/navigation";
import { Separator } from "@/components/ui/separator";

const pageTitles: Record<string, { title: string; subtitle: string }> = {
  "/dashboard": {
    title: "Observatoire National",
    subtitle: "Vue globale de l'impact des préconisations CESER",
  },
  "/analysis": {
    title: "Analyse Documentaire",
    subtitle: "Comparaison d'un document cible contre la base légale",
  },
  "/admin/ingest": {
    title: "Administration & Ingestion",
    subtitle: "Alimentation des bases vectorielles",
  },
};

export function Header() {
  const pathname = usePathname();
  const pageInfo = pageTitles[pathname] || {
    title: "Signaux Faibles CESER",
    subtitle: "Plateforme d'analyse IA",
  };

  return (
    <header className="flex-shrink-0 border-b bg-white">
      <div className="flex h-16 items-center justify-between px-6 lg:px-8">
        <div>
          <h2 className="text-lg font-semibold text-[var(--color-ceser-blue)]">
            {pageInfo.title}
          </h2>
          <p className="text-sm text-muted-foreground">{pageInfo.subtitle}</p>
        </div>
        <div className="flex items-center gap-3">
          <Separator orientation="vertical" className="h-6" />
          <div className="text-right">
            <p className="text-xs font-medium text-muted-foreground">
              République Française
            </p>
            <p className="text-[10px] text-muted-foreground/60">
              CESER de France
            </p>
          </div>
        </div>
      </div>
    </header>
  );
}
