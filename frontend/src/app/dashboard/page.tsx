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
  CheckCircle2,
  ArrowUpRight,
  ArrowDownRight,
  Scale,
  BookOpen,
} from "lucide-react";
import { toast } from "sonner";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

interface RegionStat {
  region: string;
  region_id: string;
  documents_count: number;
  total_precos: number;
  matched_precos: number;
  taux_conversion: number;
  score_2_count: number;
  score_1_count: number;
  score_0_count: number;
}

interface DocumentRanking {
  filename: string;
  region: string;
  total_precos: number;
  matched_precos: number;
  taux_conversion: number;
  avg_similarity: number;
  score_2_count: number;
  score_1_count: number;
  score_0_count: number;
}

interface LegalReference {
  legal_doc: string;
  citation_count: number;
}

interface DashboardStats {
  kpis: {
    taux_conversion_global: number;
    documents_analyses: number;
    regions_couvertes: number;
    preconisations_extraites: number;
    preconisations_matchees: number;
  };
  comparateur_regional: RegionStat[];
  score_distribution: { score_0: number; score_1: number; score_2: number };
  similarity_buckets: { range: string; count: number }[];
  top_documents: DocumentRanking[];
  bottom_documents: DocumentRanking[];
  top_legal_refs: LegalReference[];
}

const COLORS = {
  green: "var(--color-ceser-green)",
  greenLight: "var(--color-ceser-green-light)",
  gold: "var(--color-ceser-gold)",
  red: "var(--color-ceser-red)",
  neutral: "var(--color-ceser-neutral)",
  blue: "var(--color-ceser-blue)",
  blueLight: "var(--color-ceser-blue-light)",
};

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/dashboard/stats`);
      if (!res.ok) throw new Error("Erreur serveur");
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

  const kpiCards = [
    {
      title: "Taux de conversion",
      value: stats ? `${stats.kpis.taux_conversion_global}%` : "—",
      subtitle: "Préconisations reprises dans la loi",
      icon: TrendingUp,
      accent: "text-[var(--color-ceser-green)]",
      bg: "bg-[var(--color-ceser-green)]/5",
    },
    {
      title: "Documents analysés",
      value: stats ? stats.kpis.documents_analyses.toString() : "0",
      subtitle: "Rapports CESER traités",
      icon: FileText,
      accent: "text-[var(--color-ceser-blue)]",
      bg: "bg-[var(--color-ceser-blue)]/5",
    },
    {
      title: "Régions couvertes",
      value: stats ? stats.kpis.regions_couvertes.toString() : "0",
      subtitle: `sur 8 CESER régionaux`,
      icon: MapPin,
      accent: "text-[var(--color-ceser-gold)]",
      bg: "bg-[var(--color-ceser-gold)]/5",
    },
    {
      title: "Préconisations extraites",
      value: stats ? stats.kpis.preconisations_extraites.toString() : "0",
      subtitle: stats
        ? `dont ${stats.kpis.preconisations_matchees} matchées`
        : "Total cumulé",
      icon: BarChart3,
      accent: "text-[var(--color-ceser-blue-light)]",
      bg: "bg-[var(--color-ceser-blue-light)]/5",
    },
  ];

  const regionChartData = stats
    ? [...stats.comparateur_regional]
        .sort((a, b) => a.region.localeCompare(b.region))
        .map((r) => ({
          name: r.region,
          "Reprises directes": r.score_2_count,
          "Reprises partielles": r.score_1_count,
          "Non retrouvées": r.score_0_count,
          taux: r.taux_conversion,
        }))
    : [];

  const scoreData = stats
    ? [
        {
          name: "Reprise directe",
          value: stats.score_distribution.score_2,
          color: COLORS.green,
        },
        {
          name: "Reprise partielle",
          value: stats.score_distribution.score_1,
          color: COLORS.greenLight,
        },
        {
          name: "Non retrouvé",
          value: stats.score_distribution.score_0,
          color: COLORS.neutral,
        },
      ].filter((d) => d.value > 0)
    : [];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* KPIs */}
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
            {loading && (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            )}
            <Badge
              variant={error ? "destructive" : "secondary"}
              className="cursor-pointer text-xs transition-colors"
              onClick={fetchStats}
            >
              {error
                ? "Erreur (réessayer)"
                : loading
                  ? "Mise à jour..."
                  : "Données temps réel"}
            </Badge>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {kpiCards.map((kpi) => (
            <Card
              key={kpi.title}
              className="border-border/60 shadow-sm transition-shadow hover:shadow-md"
            >
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {kpi.title}
                </CardTitle>
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-lg ${kpi.bg}`}
                >
                  <kpi.icon className={`h-4 w-4 ${kpi.accent}`} />
                </div>
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

      {/* Row 2: Comparateur régional + Score distribution */}
      {stats && (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Comparateur régional — stacked bar */}
          <Card className="border-border/60 lg:col-span-2">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--color-ceser-blue)]/10">
                  <BarChart3 className="h-3.5 w-3.5 text-[var(--color-ceser-blue)]" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">
                    Comparateur régional
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">
                    Répartition des scores par région CESER
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {regionChartData.length > 0 ? (
                <ResponsiveContainer
                  width="100%"
                  height={Math.max(220, regionChartData.length * 50)}
                >
                  <BarChart
                    data={regionChartData}
                    layout="vertical"
                    margin={{ left: 10, right: 30, top: 5, bottom: 5 }}
                  >
                    <XAxis
                      type="number"
                      allowDecimals={false}
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={130}
                      tick={{ fontSize: 11 }}
                    />
                    <Tooltip
                      formatter={(value: number, name: string) => [
                        `${value} précos`,
                        name,
                      ]}
                      contentStyle={{
                        fontSize: 12,
                        borderRadius: 8,
                        border: "1px solid #e5e7eb",
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar
                      dataKey="Reprises directes"
                      stackId="a"
                      fill={COLORS.green}
                      radius={[0, 0, 0, 0]}
                    />
                    <Bar
                      dataKey="Reprises partielles"
                      stackId="a"
                      fill={COLORS.greenLight}
                    />
                    <Bar
                      dataKey="Non retrouvées"
                      stackId="a"
                      fill={COLORS.neutral}
                      radius={[0, 4, 4, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Aucune donnée régionale disponible
                </p>
              )}
            </CardContent>
          </Card>

          {/* Score distribution — donut */}
          <Card className="border-border/60">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-muted">
                  <Scale className="h-3.5 w-3.5 text-muted-foreground" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">
                    Répartition globale
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">
                    {stats.kpis.preconisations_extraites} préconisations
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {scoreData.length > 0 ? (
                <div className="space-y-4">
                  <ResponsiveContainer width="100%" height={180}>
                    <PieChart>
                      <Pie
                        data={scoreData}
                        cx="50%"
                        cy="50%"
                        innerRadius={45}
                        outerRadius={75}
                        paddingAngle={3}
                        dataKey="value"
                      >
                        {scoreData.map((entry, i) => (
                          <Cell key={i} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(value: number) => [
                          `${value} préconisations`,
                          "",
                        ]}
                        contentStyle={{
                          fontSize: 12,
                          borderRadius: 8,
                          border: "1px solid #e5e7eb",
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                    <div className="space-y-2">
                    {scoreData.map((d) => (
                      <div
                        key={d.name}
                        className="flex items-center justify-between"
                      >
                        <div className="flex items-center gap-2">
                          <div
                            className="h-2.5 w-2.5 rounded-full shrink-0"
                            style={{ backgroundColor: d.color }}
                          />
                          <span className="text-xs text-muted-foreground">
                            {d.name}
                          </span>
                        </div>
                        <span className="text-xs font-semibold">
                          {d.value}{" "}
                          <span className="font-normal text-muted-foreground">
                            (
                            {(
                              (d.value /
                                stats.kpis.preconisations_extraites) *
                              100
                            ).toFixed(0)}
                            %)
                          </span>
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Aucune donnée
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Row 3: Docs & moy précos par région + Top legal refs */}
      {stats && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Nombre de docs + Moyenne précos/doc par région */}
          <Card className="border-border/60">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--color-ceser-blue)]/10">
                  <FileText className="h-3.5 w-3.5 text-[var(--color-ceser-blue)]" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">
                    Documents et préconisations par région
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">
                    Nombre de documents analysés et moyenne de reco par document
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {stats.comparateur_regional.length > 0 ? (
                <>
                  <div>
                    <p className="mb-2 text-xs font-medium text-muted-foreground">
                      Nombre de documents par région
                    </p>
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart
                        data={[...stats.comparateur_regional].sort(
                          (a, b) => a.region.localeCompare(b.region)
                        )}
                        margin={{ left: 0, right: 10, top: 5, bottom: 5 }}
                      >
                        <XAxis
                          dataKey="region"
                          tick={{ fontSize: 10 }}
                          interval={0}
                          angle={-25}
                          textAnchor="end"
                          height={50}
                        />
                        <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={28} />
                        <Tooltip
                          formatter={(value: number) => [`${value} documents`, "Documents"]}
                          contentStyle={{
                            fontSize: 12,
                            borderRadius: 8,
                            border: "1px solid #e5e7eb",
                          }}
                        />
                        <Bar
                          dataKey="documents_count"
                          name="Documents"
                          fill={COLORS.blue}
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div>
                    <p className="mb-2 text-xs font-medium text-muted-foreground">
                      Moyenne de préconisations par document
                    </p>
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart
                        data={[...stats.comparateur_regional]
                          .filter((r) => r.documents_count > 0)
                          .map((r) => ({
                            region: r.region,
                            moy_precos: Math.round(
                              (r.total_precos / r.documents_count) * 10
                            ) / 10,
                          }))
                          .sort((a, b) => a.region.localeCompare(b.region))}
                        margin={{ left: 0, right: 10, top: 5, bottom: 5 }}
                      >
                        <XAxis
                          dataKey="region"
                          tick={{ fontSize: 10 }}
                          interval={0}
                          angle={-25}
                          textAnchor="end"
                          height={50}
                        />
                        <YAxis allowDecimals={true} tick={{ fontSize: 11 }} width={28} />
                        <Tooltip
                          formatter={(value: number) => [
                            `${value} préconisations / doc`,
                            "Moyenne",
                          ]}
                          contentStyle={{
                            fontSize: 12,
                            borderRadius: 8,
                            border: "1px solid #e5e7eb",
                          }}
                        />
                        <Bar
                          dataKey="moy_precos"
                          name="Moy. précos / doc"
                          fill={COLORS.greenLight}
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </>
              ) : (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Aucune donnée régionale
                </p>
              )}
            </CardContent>
          </Card>

          {/* Top legal references */}
          <Card className="border-border/60">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--color-ceser-gold)]/10">
                  <BookOpen className="h-3.5 w-3.5 text-[var(--color-ceser-gold)]" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">
                    Textes légaux les plus cités
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">
                    Base nationale de référence
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {stats.top_legal_refs.length > 0 ? (
                <div className="space-y-2">
                  {stats.top_legal_refs.map((ref, i) => {
                    const maxCount = stats.top_legal_refs[0]?.citation_count || 1;
                    const pct = (ref.citation_count / maxCount) * 100;
                    return (
                      <div key={i} className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span
                            className="max-w-[280px] truncate text-xs text-foreground"
                            title={ref.legal_doc}
                          >
                            {ref.legal_doc}
                          </span>
                          <Badge variant="secondary" className="text-[10px]">
                            {ref.citation_count}×
                          </Badge>
                        </div>
                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${pct}%`,
                              backgroundColor: COLORS.gold,
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Aucune référence légale
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Row 4: Top & Bottom documents */}
      {stats && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Top performers */}
          <Card className="border-border/60">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--color-ceser-green)]/10">
                  <ArrowUpRight className="h-3.5 w-3.5 text-[var(--color-ceser-green)]" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">
                    Meilleurs taux de conversion
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">
                    Documents les plus repris dans la loi
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {stats.top_documents.length > 0 ? (
                <div className="space-y-2.5">
                  {stats.top_documents.map((doc, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 rounded-lg border border-border/40 bg-muted/20 px-3 py-2"
                    >
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--color-ceser-green)]/10 text-xs font-bold text-[var(--color-ceser-green)]">
                        {i + 1}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p
                          className="truncate text-xs font-medium text-foreground"
                          title={doc.filename}
                        >
                          {doc.filename}
                        </p>
                        <p className="text-[10px] text-muted-foreground">
                          {doc.region} · {doc.matched_precos}/{doc.total_precos}{" "}
                          matchées · sim. moy. {doc.avg_similarity}%
                        </p>
                      </div>
                      <div className="shrink-0 text-right">
                        <span className="text-sm font-bold text-[var(--color-ceser-green)]">
                          {doc.taux_conversion}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Aucun document
                </p>
              )}
            </CardContent>
          </Card>

          {/* Worst performers — signals faibles */}
          <Card className="border-border/60">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--color-ceser-neutral)]/10">
                  <ArrowDownRight className="h-3.5 w-3.5 text-[var(--color-ceser-neutral)]" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">
                    Signaux faibles
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">
                    Documents les moins repris — potentiel législatif inexploité
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {stats.bottom_documents.length > 0 ? (
                <div className="space-y-2.5">
                  {stats.bottom_documents.map((doc, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 rounded-lg border border-border/40 bg-muted/20 px-3 py-2"
                    >
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--color-ceser-neutral)]/10 text-xs font-bold text-[var(--color-ceser-neutral)]">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p
                          className="truncate text-xs font-medium text-foreground"
                          title={doc.filename}
                        >
                          {doc.filename}
                        </p>
                        <p className="text-[10px] text-muted-foreground">
                          {doc.region} · {doc.matched_precos}/{doc.total_precos}{" "}
                          matchées · {doc.score_0_count} non retrouvées
                        </p>
                      </div>
                      <div className="shrink-0 text-right">
                        <span className="text-sm font-bold text-[var(--color-ceser-neutral)]">
                          {doc.taux_conversion}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Aucun document
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Loading state */}
      {loading && !stats && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-[var(--color-ceser-blue)]" />
            <p className="mt-3 text-sm text-muted-foreground">
              Chargement du tableau de bord...
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
