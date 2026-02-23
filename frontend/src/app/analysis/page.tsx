"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  FileSearch,
  Upload,
  ArrowRight,
  CheckCircle2,
  XCircle,
  MinusCircle,
  Loader2,
  ExternalLink,
  X,
} from "lucide-react";

interface PreconisationResult {
  preconisation: {
    id: number;
    preconisation: string;
    source_doc: string;
    page: number;
  };
  match: {
    score_reutilisation: number;
    score_similarite: number;
    justification: string;
    legal_source_doc: string;
    legal_page: number;
    extrait_legal_exact: string;
  } | null;
}

interface AnalysisState {
  status: "idle" | "processing" | "completed" | "failed";
  progress: number;
  message: string;
  results: PreconisationResult[];
  tauxConversion: number;
  totalPreconisations: number;
  matchedPreconisations: number;
  sourceDocument: string;
}

function ScoreIcon({ score }: { score: number }) {
  switch (score) {
    case 2:
      return <CheckCircle2 className="h-5 w-5 text-[var(--color-ceser-green)]" />;
    case 1:
      return <MinusCircle className="h-5 w-5 text-[var(--color-ceser-gold)]" />;
    default:
      return <XCircle className="h-5 w-5 text-[var(--color-ceser-red)]" />;
  }
}

function ScoreBadge({ score }: { score: number }) {
  const labels: Record<number, { text: string; variant: "default" | "secondary" | "destructive" }> = {
    2: { text: "Reprise littérale", variant: "default" },
    1: { text: "Influence indirecte", variant: "secondary" },
    0: { text: "Non retrouvé", variant: "destructive" },
  };
  const label = labels[score] || labels[0];
  return <Badge variant={label.variant}>{label.text}</Badge>;
}

function SimilarityGauge({ percent }: { percent: number }) {
  const color =
    percent >= 70
      ? "var(--color-ceser-green)"
      : percent >= 40
        ? "var(--color-ceser-gold)"
        : "var(--color-ceser-red)";

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 flex-1 rounded-full bg-muted">
        <div
          className="h-2 rounded-full transition-all"
          style={{ width: `${percent}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-sm font-semibold" style={{ color }}>
        {Math.round(percent)}%
      </span>
    </div>
  );
}

function PdfModal({
  filename,
  page,
  onClose,
}: {
  filename: string;
  page: number;
  onClose: () => void;
}) {
  const pdfUrl = `http://localhost:8000/api/documents/pdf/${encodeURIComponent(filename)}#page=${page}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="relative flex h-[90vh] w-full max-w-5xl flex-col rounded-lg bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <div>
            <h3 className="text-sm font-semibold">{filename}</h3>
            <p className="text-xs text-muted-foreground">Page {page}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <iframe
          src={pdfUrl}
          className="flex-1 rounded-b-lg"
          title={`${filename} - page ${page}`}
        />
      </div>
    </div>
  );
}

export default function AnalysisPage() {
  const [analysis, setAnalysis] = useState<AnalysisState>({
    status: "idle",
    progress: 0,
    message: "",
    results: [],
    tauxConversion: 0,
    totalPreconisations: 0,
    matchedPreconisations: 0,
    sourceDocument: "",
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [pdfModal, setPdfModal] = useState<{ filename: string; page: number } | null>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files?.[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleAnalysis = async () => {
    if (!selectedFile) return;

    setAnalysis({ ...analysis, status: "processing", progress: 5, message: "Envoi du document..." });

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch("http://localhost:8000/api/analysis/run", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      const taskId = data.task_id;

      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await fetch(`http://localhost:8000/api/analysis/status/${taskId}`);

          if (!statusRes.ok) {
            clearInterval(pollInterval);
            setAnalysis((prev) => ({
              ...prev,
              status: "failed",
              message: statusRes.status === 404
                ? "Tâche perdue (le serveur a redémarré). Relancez l'analyse."
                : `Erreur serveur (${statusRes.status})`,
            }));
            return;
          }

          const status = await statusRes.json();

          setAnalysis((prev) => ({
            ...prev,
            progress: status.progress * 100,
            message: status.message,
          }));

          if (status.status === "completed" && status.result) {
            clearInterval(pollInterval);
            setAnalysis({
              status: "completed",
              progress: 100,
              message: status.message,
              results: status.result.results,
              tauxConversion: status.result.taux_conversion,
              totalPreconisations: status.result.total_preconisations,
              matchedPreconisations: status.result.matched_preconisations,
              sourceDocument: status.result.source_document,
            });
          } else if (status.status === "failed") {
            clearInterval(pollInterval);
            setAnalysis((prev) => ({
              ...prev,
              status: "failed",
              message: status.message,
            }));
          }
        } catch {
          clearInterval(pollInterval);
          setAnalysis((prev) => ({
            ...prev,
            status: "failed",
            message: "Erreur de connexion au serveur",
          }));
        }
      }, 2000);
    } catch {
      setAnalysis((prev) => ({
        ...prev,
        status: "failed",
        message: "Impossible de contacter le serveur backend",
      }));
    }
  };

  return (
    <div className="space-y-6">
      {pdfModal && (
        <PdfModal
          filename={pdfModal.filename}
          page={pdfModal.page}
          onClose={() => setPdfModal(null)}
        />
      )}

      {/* Input Section */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/60">
          <CardHeader>
            <CardTitle className="text-base font-semibold">
              Document cible
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              Sélectionnez un document existant ou soumettez un nouveau fichier
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <Select>
              <SelectTrigger>
                <SelectValue placeholder="Choisir un document existant..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Toutes régions</SelectItem>
              </SelectContent>
            </Select>

            <div className="relative text-center text-xs text-muted-foreground">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t" />
              </div>
              <span className="relative bg-card px-2">ou</span>
            </div>

            <div
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
              onDragLeave={() => setIsDragOver(false)}
              className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
                isDragOver
                  ? "border-[var(--color-ceser-blue)] bg-[var(--color-ceser-blue-pale)]"
                  : "border-border hover:border-[var(--color-ceser-blue-light)]"
              }`}
            >
              <Upload className="h-8 w-8 text-muted-foreground/50" />
              <p className="mt-2 text-sm text-muted-foreground">
                Glissez un fichier PDF/Word ici
              </p>
              <label className="mt-2 cursor-pointer text-xs font-medium text-[var(--color-ceser-blue)] hover:underline">
                ou parcourir
                <input
                  type="file"
                  accept=".pdf,.docx,.doc,.txt"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </label>
              {selectedFile && (
                <Badge variant="secondary" className="mt-3">
                  {selectedFile.name}
                </Badge>
              )}
            </div>

            <Button
              onClick={handleAnalysis}
              disabled={!selectedFile || analysis.status === "processing"}
              className="w-full bg-[var(--color-ceser-blue)] hover:bg-[var(--color-ceser-blue-light)]"
            >
              {analysis.status === "processing" ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Analyse en cours...
                </>
              ) : (
                <>
                  <FileSearch className="mr-2 h-4 w-4" />
                  Lancer l&apos;analyse
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Progress / KPI Card */}
        <Card className="border-border/60">
          <CardHeader>
            <CardTitle className="text-base font-semibold">
              {analysis.status === "completed" ? "Résultat global" : "Progression"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {analysis.status === "idle" && (
              <div className="flex h-48 items-center justify-center text-center">
                <div>
                  <FileSearch className="mx-auto h-12 w-12 text-muted-foreground/30" />
                  <p className="mt-3 text-sm text-muted-foreground">
                    Sélectionnez un document et lancez l&apos;analyse pour voir les résultats
                  </p>
                </div>
              </div>
            )}

            {analysis.status === "processing" && (
              <div className="space-y-4">
                <Progress value={analysis.progress} className="h-2" />
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-[var(--color-ceser-blue)]" />
                  <p className="text-sm text-muted-foreground">{analysis.message}</p>
                </div>
                <div className="rounded-lg bg-muted/50 p-4">
                  <p className="text-xs text-muted-foreground">
                    Le pipeline RAG analyse le document en 4 étapes : extraction des préconisations,
                    recherche vectorielle, validation sémantique et scoring.
                  </p>
                </div>
              </div>
            )}

            {analysis.status === "completed" && (
              <div className="space-y-4">
                <div className="text-center">
                  <div className="text-5xl font-bold text-[var(--color-ceser-blue)]">
                    {analysis.tauxConversion}%
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Taux de conversion des préconisations
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-lg bg-muted/50 p-3 text-center">
                    <div className="text-2xl font-semibold">{analysis.totalPreconisations}</div>
                    <p className="text-xs text-muted-foreground">Préconisations extraites</p>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-3 text-center">
                    <div className="text-2xl font-semibold text-[var(--color-ceser-green)]">
                      {analysis.matchedPreconisations}
                    </div>
                    <p className="text-xs text-muted-foreground">Retrouvées dans la loi</p>
                  </div>
                </div>
              </div>
            )}

            {analysis.status === "failed" && (
              <div className="flex h-48 items-center justify-center text-center">
                <div>
                  <XCircle className="mx-auto h-12 w-12 text-[var(--color-ceser-red)]" />
                  <p className="mt-3 text-sm text-destructive">{analysis.message}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Results Split View */}
      {analysis.status === "completed" && analysis.results.length > 0 && (
        <Card className="border-border/60">
          <CardHeader>
            <CardTitle className="text-base font-semibold">
              Détail des préconisations — {analysis.sourceDocument}
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              Vue comparative : préconisations CESER vs textes légaux
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {analysis.results.map((result) => (
              <div
                key={result.preconisation.id}
                className="grid gap-4 rounded-lg border border-border/60 p-4 lg:grid-cols-2"
              >
                {/* Left: Preconisation */}
                <div className="space-y-2">
                  <div className="flex items-start gap-2">
                    <ScoreIcon score={result.match?.score_reutilisation ?? 0} />
                    <div className="flex-1">
                      <div className="mb-1 flex items-center gap-2">
                        <span className="text-xs font-medium text-muted-foreground">
                          Préconisation #{result.preconisation.id}
                        </span>
                        <ScoreBadge score={result.match?.score_reutilisation ?? 0} />
                      </div>
                      <p className="text-sm leading-relaxed">
                        {result.preconisation.preconisation}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Source : {result.preconisation.source_doc}, p.{result.preconisation.page}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Right: Legal match */}
                <div className="space-y-2 border-l border-border/40 pl-4">
                  {result.match && result.match.score_reutilisation > 0 ? (
                    <>
                      <div className="flex items-center gap-2">
                        <ArrowRight className="h-4 w-4 text-[var(--color-ceser-blue)]" />
                        <span className="text-xs font-semibold text-[var(--color-ceser-blue)]">
                          Correspondance légale
                        </span>
                      </div>
                      <blockquote className="border-l-2 border-[var(--color-ceser-blue)] bg-[var(--color-ceser-blue-pale)] p-3 text-sm italic leading-relaxed">
                        &laquo; {result.match.extrait_legal_exact} &raquo;
                      </blockquote>
                      <button
                        onClick={() =>
                          setPdfModal({
                            filename: result.match!.legal_source_doc,
                            page: result.match!.legal_page,
                          })
                        }
                        className="inline-flex items-center gap-1 text-xs font-medium text-[var(--color-ceser-blue)] hover:underline"
                      >
                        <ExternalLink className="h-3 w-3" />
                        {result.match.legal_source_doc}, p.{result.match.legal_page}
                      </button>
                      <div className="mt-1">
                        <p className="mb-1 text-xs font-medium text-muted-foreground">
                          Score de reprise
                        </p>
                        <SimilarityGauge percent={result.match.score_similarite} />
                      </div>
                    </>
                  ) : (
                    <div className="flex h-full items-center justify-center">
                      <p className="text-sm text-muted-foreground italic">
                        {result.match?.justification || "Aucune correspondance trouvée"}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
