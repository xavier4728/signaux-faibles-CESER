import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp,
  FileText,
  MapPin,
  BarChart3,
} from "lucide-react";

const kpiCards = [
  {
    title: "Taux de conversion global",
    value: "—",
    subtitle: "Préconisations reprises dans la loi",
    icon: TrendingUp,
    accent: "text-[var(--color-ceser-green)]",
  },
  {
    title: "Documents analysés",
    value: "0",
    subtitle: "Rapports CESER indexés",
    icon: FileText,
    accent: "text-[var(--color-ceser-blue)]",
  },
  {
    title: "Régions couvertes",
    value: "8",
    subtitle: "CESER régionaux",
    icon: MapPin,
    accent: "text-[var(--color-ceser-gold)]",
  },
  {
    title: "Préconisations extraites",
    value: "0",
    subtitle: "Total cumulé",
    icon: BarChart3,
    accent: "text-[var(--color-ceser-blue-light)]",
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <section>
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-foreground">
              Indicateurs clés
            </h3>
            <p className="text-sm text-muted-foreground">
              Synthèse nationale de l&apos;impact des préconisations CESER
            </p>
          </div>
          <Badge variant="secondary" className="text-xs">
            Données en attente d&apos;ingestion
          </Badge>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {kpiCards.map((kpi) => (
            <Card key={kpi.title} className="border-border/60">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {kpi.title}
                </CardTitle>
                <kpi.icon className={`h-4 w-4 ${kpi.accent}`} />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-foreground">
                  {kpi.value}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {kpi.subtitle}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/60">
          <CardHeader>
            <CardTitle className="text-base font-semibold">
              Comparateur régional
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              Score d&apos;impact par région CESER
            </p>
          </CardHeader>
          <CardContent>
            <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-border bg-muted/30">
              <div className="text-center">
                <BarChart3 className="mx-auto h-10 w-10 text-muted-foreground/40" />
                <p className="mt-2 text-sm text-muted-foreground">
                  Le graphique comparatif apparaîtra après ingestion des données
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/60">
          <CardHeader>
            <CardTitle className="text-base font-semibold">
              Cartographie nationale
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              Thématiques par territoire
            </p>
          </CardHeader>
          <CardContent>
            <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-border bg-muted/30">
              <div className="text-center">
                <MapPin className="mx-auto h-10 w-10 text-muted-foreground/40" />
                <p className="mt-2 text-sm text-muted-foreground">
                  La carte de France apparaîtra après ingestion des données
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="text-base font-semibold">
            Timeline macro
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Frise chronologique : anticipation des thématiques CESER vs
            décisions politiques
          </p>
        </CardHeader>
        <CardContent>
          <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-border bg-muted/30">
            <div className="text-center">
              <TrendingUp className="mx-auto h-10 w-10 text-muted-foreground/40" />
              <p className="mt-2 text-sm text-muted-foreground">
                La frise chronologique apparaîtra après ingestion et analyse
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
