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

interface CategoryStatWithRegions {
  category: string;
  regions: Record<string, number>;
}

interface RegionOverlap {
  region_ids: string[];
  region_labels: Record<string, string>;
  matrix: number[][];
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
  category_stats: CategoryStatWithRegions[];
  region_overlap: RegionOverlap | null;
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
  /** Thématiques affichées dans le graphique "Part des régions par catégorie". Vide = toutes. */
  const [chartSelectedThemes, setChartSelectedThemes] = useState<Set<string>>(new Set());

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
                      formatter={(value: number | undefined, name: string | undefined) => [
                        `${value ?? 0} précos`,
                        name ?? "",
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
                        formatter={(value: number | undefined) => [
                          `${value ?? 0} préconisations`,
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
                          formatter={(value: number | undefined) => [`${value ?? 0} documents`, "Documents"]}
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
                          formatter={(value: number | undefined) => [
                            `${value ?? 0} préconisations / doc`,
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

      {/* Row 4: Part des régions par catégorie + Recoupement entre régions */}
      {stats && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Part des régions par catégorie */}
          <Card className="border-border/60">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--color-ceser-blue)]/10">
                  <BarChart3 className="h-3.5 w-3.5 text-[var(--color-ceser-blue)]" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">
                    Part des régions par catégorie
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">
                    Pour chaque région, part des préconisations par thématique
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {stats.category_stats.length > 0 && stats.comparateur_regional.length > 0 ? (
                (() => {
                  const regionOrder = [...stats.comparateur_regional].sort((a, b) => a.region.localeCompare(b.region));
                  const categoryOrder = [...new Set(stats.category_stats.map((s) => s.category))].sort((a, b) => a.localeCompare(b));
                  const allSelected = chartSelectedThemes.size === 0;
                  const visibleCategories = allSelected
                    ? categoryOrder
                    : categoryOrder.filter((c) => chartSelectedThemes.has(c));
                  const effectiveCategories = visibleCategories.length > 0 ? visibleCategories : categoryOrder;

                  const toggleTheme = (category: string) => {
                    setChartSelectedThemes((prev) => {
                      const next = new Set(prev);
                      if (prev.size === 0) {
                        return new Set([category]);
                      }
                      if (next.has(category)) {
                        next.delete(category);
                        return next;
                      }
                      next.add(category);
                      return next;
                    });
                  };
                  const isThemeActive = (cat: string) => allSelected || chartSelectedThemes.has(cat);

                  // Données du graphique : uniquement les thématiques visibles
                  const regionChartData = regionOrder.map((r) => {
                    const row: Record<string, string | number> = { region: r.region };
                    effectiveCategories.forEach((cat) => {
                      const stat = stats.category_stats.find((s) => s.category === cat);
                      row[cat] = stat?.regions[r.region_id] ?? 0;
                    });
                    return row;
                  });

                  const categoryColors = [
                    "#7dd3fc", "#86efac", "#fde047", "#fdba74", "#fca5a5", "#c4b5fd",
                    "#67e8f9", "#bef264", "#f9a8d4", "#a5b4fc", "#5eead4", "#a8a29e",
                  ];
                  const totalByCategory = categoryOrder.map((cat, i) => {
                    const stat = stats.category_stats.find((s) => s.category === cat);
                    const total = stat ? Object.values(stat.regions).reduce((a, b) => a + b, 0) : 0;
                    return { category: cat, total, color: categoryColors[i % categoryColors.length] };
                  });

                  return (
                    <div className="space-y-3">
                      <p className="text-xs text-muted-foreground">
                        Cliquez sur une thématique pour afficher uniquement celle(s) choisie(s). Recliquez pour réinclure, ou « Tout afficher » pour tout afficher.
                      </p>
                      <div className="flex flex-wrap items-center gap-1.5 border-b border-border/50 pb-2">
                        {!allSelected && (
                          <button
                            type="button"
                            onClick={() => setChartSelectedThemes(new Set())}
                            className="rounded-md border border-border bg-muted/50 px-2 py-1 text-xs font-medium text-muted-foreground transition hover:bg-muted hover:text-foreground"
                          >
                            Tout afficher
                          </button>
                        )}
                        {totalByCategory.map(({ category, total, color }) => (
                          <button
                            key={category}
                            type="button"
                            onClick={() => toggleTheme(category)}
                            className={`flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition ${
                              isThemeActive(category)
                                ? "border-transparent font-medium"
                                : "border-border/60 bg-muted/30 opacity-60 hover:opacity-80"
                            }`}
                            style={isThemeActive(category) ? { backgroundColor: `${color}20`, borderColor: color } : undefined}
                            title={isThemeActive(category) ? "Masquer cette thématique" : "Afficher cette thématique"}
                          >
                            <span className="h-2 w-2 shrink-0 rounded-sm" style={{ backgroundColor: color }} aria-hidden />
                            <span>{category}</span>
                            <span className="tabular-nums text-muted-foreground">{total}</span>
                          </button>
                        ))}
                      </div>
                      <ResponsiveContainer width="100%" height={Math.max(220, regionChartData.length * 36)}>
                        <BarChart
                          data={regionChartData}
                          layout="vertical"
                          margin={{ left: 4, right: 20, top: 5, bottom: 5 }}
                        >
                          <XAxis type="number" allowDecimals={false} tick={{ fontSize: 10 }} />
                          <YAxis type="category" dataKey="region" width={140} tick={{ fontSize: 10 }} />
                          <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8, border: "1px solid #e5e7eb" }} />
                          <Legend wrapperStyle={{ fontSize: 10 }} />
                          {effectiveCategories.map((cat, i) => (
                            <Bar
                              key={cat}
                              dataKey={cat}
                              stackId="a"
                              fill={categoryColors[categoryOrder.indexOf(cat) % categoryColors.length]}
                              radius={i === 0 ? [0, 0, 0, 0] : [0, 2, 2, 0]}
                            />
                          ))}
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  );
                })()
              ) : (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Lancez le script de catégorisation : python -m scripts.compute_category_and_overlap
                </p>
              )}
            </CardContent>
          </Card>

          {/* Recoupement entre régions */}
          <Card className="border-border/60">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--color-ceser-green)]/10">
                  <MapPin className="h-3.5 w-3.5 text-[var(--color-ceser-green)]" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">
                    Recoupement entre régions
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">
                    Préconisations thématiques communes (plus la valeur est élevée, plus les régions se recoupent)
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {stats.region_overlap && stats.region_overlap.region_ids.length > 0 ? (
                (() => {
                  const ro = stats.region_overlap;
                  const ids = ro.region_ids;
                  const labels = ro.region_labels;
                  const matrix = ro.matrix;
                  const sortedByLabel = [...ids].sort((a, b) => (labels[a] || a).localeCompare(labels[b] || b));
                  const maxVal = matrix.flat().reduce((m, v) => Math.max(m, v), 0) || 1;
                  // Nuances du vert « Reprises directes » (#28A745)
                  const ceserGreenHue = 134;
                  const ceserGreenSat = 61;
                  const getHeatmapBg = (val: number, isDiagonal: boolean): { backgroundColor: string } => {
                    if (isDiagonal) return { backgroundColor: "hsl(220, 10%, 96%)" };
                    if (maxVal === 0) return { backgroundColor: "hsl(220, 10%, 99%)" };
                    const t = val / maxVal;
                    const lightness = 96 - t * 55;
                    return { backgroundColor: `hsl(${ceserGreenHue}, ${ceserGreenSat}%, ${lightness}%)` };
                  };
                  return (
                    <div className="space-y-3">
                      <div className="flex justify-end">
                        <div className="flex items-center gap-2 rounded-lg border border-border/50 bg-muted/5 px-3 py-1.5 text-[10px] text-muted-foreground">
                          <span>pas similaire</span>
                          <div className="flex h-3 w-20 overflow-hidden rounded-full border border-border/40">
                            {[0, 0.25, 0.5, 0.75, 1].map((t, k) => (
                              <div
                                key={k}
                                className="flex-1"
                                style={{ backgroundColor: `hsl(${ceserGreenHue}, ${ceserGreenSat}%, ${96 - t * 55}%)` }}
                              />
                            ))}
                          </div>
                          <span>similaire</span>
                        </div>
                      </div>
                      <div className="overflow-x-auto rounded-lg border border-border/50">
                        <table className="w-full min-w-[320px] border-collapse text-xs">
                          <thead>
                            <tr>
                              <th className="rounded-tl-lg border border-border/60 bg-muted/50 p-1.5 text-left font-medium"></th>
                              {sortedByLabel.map((id) => (
                                <th key={id} className="border border-border/60 bg-muted/50 p-1.5 text-center font-medium truncate max-w-[80px]" title={labels[id] || id}>
                                  {(labels[id] || id).split(" ")[0]}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {sortedByLabel.map((idI) => (
                              <tr key={idI}>
                                <td className="border border-border/60 p-1.5 font-medium truncate max-w-[90px]" title={labels[idI] || idI}>
                                  {(labels[idI] || idI).split(" ")[0]}
                                </td>
                                {sortedByLabel.map((idJ) => {
                                  const idxI = ids.indexOf(idI);
                                  const idxJ = ids.indexOf(idJ);
                                  const val = matrix[idxI]?.[idxJ] ?? 0;
                                  const isDiagonal = idxI === idxJ;
                                  return (
                                    <td
                                      key={idJ}
                                      className="border border-border/60 p-1.5 text-center transition-colors"
                                      style={getHeatmapBg(val, isDiagonal)}
                                      title={`${labels[idI]} ↔ ${labels[idJ]} : ${val} préconisations en commun`}
                                    >
                                      {isDiagonal ? "—" : ""}
                                    </td>
                                  );
                                })}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  );
                })()
              ) : (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Lancez le script : python -m scripts.compute_category_and_overlap
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
