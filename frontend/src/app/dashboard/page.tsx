"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp,
  FileText,
  MapPin,
  BarChart3,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";

// Définition stricte des types attendus du backend
interface DashboardStats {
  kpis: {
    taux_conversion_global: number;
    documents_analyses: number;
    regions_couvertes: number;
    preconisations_extraites: number;
  };
  comparateur_regional: Array<{
    region: string;
    count: number;
    impact_score: number;
  }>;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchStats = async () => {
    try {
      setLoading(true);
      // Utilisation de l'URL relative ou via variable d'environnement
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/dashboard/stats`);
      
      if (!res.ok) {
        throw new Error("Erreur serveur lors de la récupération des stats");
      }
      
      const data = await res.json();
      setStats(data);
      setError(false);
    } catch (err) {
      console.error(err);
      setError(true);
      toast.error("Impossible de charger les données du tableau de bord");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  // Configuration dynamique des cartes avec valeurs par défaut sécurisées
  const kpiCards = [
    {
      title: "Taux de conversion global",
      value: stats ? `${stats.kpis.taux_conversion_global}%` : "—",
      subtitle: "Préconisations reprises dans la loi",
      icon: TrendingUp,
      accent: "text-[var(--color-ceser-green)]",
    },
    {
      title: "Documents analysés",
      value: stats ? stats.kpis.documents_analyses.toString() : "0",
      subtitle: "Rapports CESER indexés",
      icon: FileText,
      accent: "text-[var(--color-ceser-blue)]",
    },
    {
      title: "Régions couvertes",
      value: stats ? stats.kpis.regions_couvertes.toString() : "0",
      subtitle: "CESER régionaux",
      icon: MapPin,
      accent: "text-[var(--color-ceser-gold)]",
    },
    {
      title: "Préconisations extraites",
      value: stats ? stats.kpis.preconisations_extraites.toString() : "0",
      subtitle: "Total cumulé",
      icon: BarChart3,
      accent: "text-[var(--color-ceser-blue-light)]",
    },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
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
          <div className="flex items-center gap-2">
            {loading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
            <Badge 
                variant={error ? "destructive" : "secondary"} 
                className="text-xs transition-colors cursor-pointer"
                onClick={fetchStats}
            >
              {error ? "Erreur de connexion (réessayer)" : loading ? "Mise à jour..." : "Données temps réel"}
            </Badge>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {kpiCards.map((kpi) => (
            <Card key={kpi.title} className="border-border/60 shadow-sm hover:shadow-md transition-shadow">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {kpi.title}
                </CardTitle>
                <kpi.icon className={`h-4 w-4 ${kpi.accent}`} />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-foreground">
                  {loading && !stats ? (
                    <div className="h-8 w-16 animate-pulse rounded bg-muted" />
                  ) : (
                    kpi.value
                  )}
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
                  Le graphique comparatif apparaîtra ici
                </p>
                {stats && stats.kpis.documents_analyses > 0 && (
                    <Badge variant="outline" className="mt-2">Données disponibles</Badge>
                )}
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
                  La carte de France apparaîtra ici
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
                La frise chronologique apparaîtra ici
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}