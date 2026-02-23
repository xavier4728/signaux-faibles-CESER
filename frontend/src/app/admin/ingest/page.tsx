"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  Upload,
  CheckCircle2,
  XCircle,
  Loader2,
  Database,
  FileText,
  AlertCircle,
} from "lucide-react";

interface LogEntry {
  timestamp: string;
  level: "info" | "success" | "error";
  message: string;
}

const databases = [
  { id: "legal_national", name: "Base Légale / Nationale", type: "legal" },
  { id: "ceser_normandie", name: "CESER Normandie", type: "ceser" },
  { id: "ceser_bretagne", name: "CESER Bretagne", type: "ceser" },
  { id: "ceser_ile_de_france", name: "CESER Île-de-France", type: "ceser" },
  { id: "ceser_occitanie", name: "CESER Occitanie", type: "ceser" },
  { id: "ceser_auvergne_rhone_alpes", name: "CESER Auvergne-Rhône-Alpes", type: "ceser" },
  { id: "ceser_nouvelle_aquitaine", name: "CESER Nouvelle-Aquitaine", type: "ceser" },
  { id: "ceser_grand_est", name: "CESER Grand Est", type: "ceser" },
  { id: "ceser_hauts_de_france", name: "CESER Hauts-de-France", type: "ceser" },
];

export default function IngestPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [targetDb, setTargetDb] = useState("");
  const [metadata, setMetadata] = useState({
    title: "",
    year: "",
    doc_type: "",
    theme: "",
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);

  const addLog = (level: LogEntry["level"], message: string) => {
    setLogs((prev) => [
      ...prev,
      { timestamp: new Date().toLocaleTimeString("fr-FR"), level, message },
    ]);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setSelectedFile(e.target.files[0]);
      addLog("info", `Fichier sélectionné : ${e.target.files[0].name}`);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files?.[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
      addLog("info", `Fichier déposé : ${e.dataTransfer.files[0].name}`);
    }
  };

  const handleSubmit = async () => {
    if (!selectedFile || !targetDb) return;

    setIsProcessing(true);
    setProgress(0);
    addLog("info", `Début de l'ingestion vers ${targetDb}...`);

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("target_db", targetDb);
    formData.append("title", metadata.title);
    if (metadata.year) formData.append("year", metadata.year);
    formData.append("doc_type", metadata.doc_type);
    formData.append("theme", metadata.theme);

    try {
      const response = await fetch("http://localhost:8000/api/ingest/single", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      const taskId = data.task_id;

      addLog("info", `Tâche créée : ${taskId}`);

      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await fetch(`http://localhost:8000/api/ingest/status/${taskId}`);

          if (!statusRes.ok) {
            clearInterval(pollInterval);
            addLog("error", statusRes.status === 404
              ? "Tâche perdue (le serveur a redémarré). Relancez l'ingestion."
              : `Erreur serveur (${statusRes.status})`);
            setIsProcessing(false);
            return;
          }

          const status = await statusRes.json();

          setProgress(status.progress * 100);
          addLog("info", status.message);

          if (status.status === "completed") {
            clearInterval(pollInterval);
            addLog("success", status.message);
            setIsProcessing(false);
            setProgress(100);
          } else if (status.status === "failed") {
            clearInterval(pollInterval);
            addLog("error", status.message);
            setIsProcessing(false);
          }
        } catch {
          clearInterval(pollInterval);
          addLog("error", "Erreur de connexion au serveur");
          setIsProcessing(false);
        }
      }, 2000);
    } catch {
      addLog("error", "Impossible de contacter le serveur backend");
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Upload Form */}
        <Card className="border-border/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <Upload className="h-5 w-5" />
              Téléchargement de document
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              Ajoutez un document PDF ou Word à une base vectorielle
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Drop zone */}
            <div
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
              onDragLeave={() => setIsDragOver(false)}
              className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors ${
                isDragOver
                  ? "border-[var(--color-ceser-blue)] bg-[var(--color-ceser-blue-pale)]"
                  : "border-border hover:border-[var(--color-ceser-blue-light)]"
              }`}
            >
              <Upload className="h-6 w-6 text-muted-foreground/50" />
              <p className="mt-2 text-sm text-muted-foreground">
                Glissez un fichier ici
              </p>
              <label className="mt-1 cursor-pointer text-xs font-medium text-[var(--color-ceser-blue)] hover:underline">
                ou parcourir
                <input
                  type="file"
                  accept=".pdf,.docx,.doc,.txt"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </label>
              {selectedFile && (
                <Badge variant="secondary" className="mt-2">
                  <FileText className="mr-1 h-3 w-3" />
                  {selectedFile.name}
                </Badge>
              )}
            </div>

            {/* Database selector */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">
                Base de destination <span className="text-destructive">*</span>
              </Label>
              <Select onValueChange={setTargetDb} value={targetDb}>
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionner la base cible..." />
                </SelectTrigger>
                <SelectContent>
                  {databases.map((db) => (
                    <SelectItem key={db.id} value={db.id}>
                      <span className="flex items-center gap-2">
                        <Database className="h-3 w-3" />
                        {db.name}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Metadata fields */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Titre du document</Label>
                <Input
                  value={metadata.title}
                  onChange={(e) => setMetadata({ ...metadata, title: e.target.value })}
                  placeholder="Ex: Rapport CESER 2020"
                  className="h-8 text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Année</Label>
                <Input
                  type="number"
                  value={metadata.year}
                  onChange={(e) => setMetadata({ ...metadata, year: e.target.value })}
                  placeholder="Ex: 2020"
                  className="h-8 text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Type de document</Label>
                <Input
                  value={metadata.doc_type}
                  onChange={(e) => setMetadata({ ...metadata, doc_type: e.target.value })}
                  placeholder="Ex: Rapport, Avis..."
                  className="h-8 text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Thématique</Label>
                <Input
                  value={metadata.theme}
                  onChange={(e) => setMetadata({ ...metadata, theme: e.target.value })}
                  placeholder="Ex: Agriculture"
                  className="h-8 text-sm"
                />
              </div>
            </div>

            <Button
              onClick={handleSubmit}
              disabled={!selectedFile || !targetDb || isProcessing}
              className="w-full bg-[var(--color-ceser-blue)] hover:bg-[var(--color-ceser-blue-light)]"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Ingestion en cours...
                </>
              ) : (
                <>
                  <Database className="mr-2 h-4 w-4" />
                  Lancer l&apos;ingestion
                </>
              )}
            </Button>

            {isProcessing && <Progress value={progress} className="h-2" />}
          </CardContent>
        </Card>

        {/* Console / Logs */}
        <Card className="border-border/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <AlertCircle className="h-5 w-5" />
              Console de traitement
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              Logs en temps réel du pipeline NLP
            </p>
          </CardHeader>
          <CardContent>
            <div className="h-[400px] overflow-y-auto rounded-lg bg-slate-950 p-4 font-mono text-xs">
              {logs.length === 0 ? (
                <p className="text-slate-500">
                  En attente d&apos;une opération d&apos;ingestion...
                </p>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className="flex gap-2 py-0.5">
                    <span className="text-slate-500">[{log.timestamp}]</span>
                    {log.level === "success" && (
                      <CheckCircle2 className="mt-0.5 h-3 w-3 flex-shrink-0 text-green-500" />
                    )}
                    {log.level === "error" && (
                      <XCircle className="mt-0.5 h-3 w-3 flex-shrink-0 text-red-500" />
                    )}
                    {log.level === "info" && (
                      <span className="text-blue-400">INFO</span>
                    )}
                    <span
                      className={
                        log.level === "error"
                          ? "text-red-400"
                          : log.level === "success"
                          ? "text-green-400"
                          : "text-slate-300"
                      }
                    >
                      {log.message}
                    </span>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
