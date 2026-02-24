"use client";

import { usePathname } from "next/navigation";
import Image from "next/image";
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

const regionalLogos = [
  { name: "Bretagne", src: "/logos/ceser-bretagne.png" },
  { name: "Centre-Val de Loire", src: "/logos/ceser-centre-val-de-loire.png" },
  { name: "Grand Est", src: "/logos/ceser-grand-est.png" },
  { name: "Hauts-de-France", src: "/logos/ceser-hauts-de-france.png" },
  { name: "La Réunion", src: "/logos/ceser-la-reunion.png" },
  { name: "Normandie", src: "/logos/ceser-normandie.png" },
  { name: "Nouvelle-Aquitaine", src: "/logos/ceser-nouvelle-aquitaine.png" },
  { name: "Pays de la Loire", src: "/logos/ceser-pays-de-la-loire.png" },
];

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
          
          <div className="hidden xl:flex items-center gap-6 mr-2">
            {regionalLogos.map((logo) => (
              <div key={logo.name} className="relative h-16 w-16 opacity-80 hover:opacity-100 transition-opacity" title={`CESER ${logo.name}`}>
                <Image
                  src={logo.src}
                  alt={logo.name}
                  fill
                  className="object-contain"
                />
              </div>
            ))}
          </div>

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