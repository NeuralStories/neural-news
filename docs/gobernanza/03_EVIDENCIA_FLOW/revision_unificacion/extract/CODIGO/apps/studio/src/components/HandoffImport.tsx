import React, { useEffect, useRef, useState } from 'react';
import { NewsArticle } from '../studio/types';
import {
  DuplicateHandoffError,
  HandoffValidationError,
  importHandoff,
} from '../lib/handoffConsumer';
import { ApiError, ApiNotReachableError, fetchStoryHandoff } from '../lib/apiClient';
import handoffSchema from '../contracts/production_handoff.v1.schema.json';

interface HandoffImportProps {
  onImportArticles: (
    articles: Omit<NewsArticle, 'id' | 'orderIndex'>[]
  ) => { importedCount: number; duplicateCount: number; duplicateDetails: string[] };
}

interface ImportFeedback {
  kind: 'ok' | 'error';
  title: string;
  details: string[];
}

/** Fases del traspaso: se muestran para que el usuario sepa dónde está. */
type ImportPhase = 'idle' | 'leyendo' | 'validando' | 'importado' | 'incompatible' | 'error';

const PHASE_LABEL: Record<ImportPhase, string> = {
  idle: 'Sin archivo',
  leyendo: 'Leyendo el documento',
  validando: 'Validando contrato e integridad',
  importado: 'Importado',
  incompatible: 'Incompatible con el contrato',
  error: 'Error de integridad',
};

/**
 * Recepción del traspaso `production_handoff.v1` emitido por el motor editorial
 * (GET /api/v1/stories/{id}/handoff o descarga del JSON). Valida el documento,
 * verifica el hash del guion y evita reimportaciones antes de añadir las
 * noticias a la redacción.
 */
export const HandoffImport: React.FC<HandoffImportProps> = ({ onImportArticles }) => {
  const [pastedJson, setPastedJson] = useState('');
  // Deep-link: /estudio?story=<id>&revision=<n> carga el traspaso sin copiar nada.
  const [deepLinkStory, setDeepLinkStory] = useState<string | null>(null);
  const [deepLinkRevision, setDeepLinkRevision] = useState<string | null>(null);
  const [phase, setPhase] = useState<ImportPhase>('idle');
  const [importedSummary, setImportedSummary] = useState<{
    handoffId: string;
    mode: string;
    stories: { title: string; revision: number; sources: number }[];
  } | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [storyId, setStoryId] = useState('');
  const [fetching, setFetching] = useState(false);
  const [feedback, setFeedback] = useState<ImportFeedback | null>(null);
  const [isWorking, setIsWorking] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setFileContent(await file.text());
    setFeedback(null);
  };

  /** Vía integrada: el traspaso se trae del motor editorial (misma validación e integridad). */
  /** Carga automática por deep-link (id + revisión en la URL). */
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('story');
    if (!id) return;
    setDeepLinkStory(id);
    setDeepLinkRevision(params.get('revision'));
    setStoryId(id);
    void handleFetchFromApi(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFetchFromApi = async (presetId?: string) => {
    const id = Number((presetId ?? storyId).trim());
    if (!Number.isInteger(id) || id <= 0) {
      setFeedback({
        kind: 'error',
        title: 'Identificador no válido',
        details: ['Introduce el número de noticia que aparece en neural.news (por ejemplo 7).'],
      });
      return;
    }
    setFetching(true);
    setFeedback(null);
    try {
      const document = await fetchStoryHandoff(id);
      await acceptDocument(document);
      setStoryId('');
    } catch (err) {
      if (err instanceof ApiNotReachableError || err instanceof ApiError) {
        setFeedback({ kind: 'error', title: 'No se pudo traer el traspaso', details: [err.message] });
      } else {
        setFeedback({
          kind: 'error',
          title: 'No se pudo traer el traspaso',
          details: [err instanceof Error ? err.message : String(err)],
        });
      }
    } finally {
      setFetching(false);
    }
  };

  const acceptDocument = async (document: unknown) => {
    setPhase('validando');
    const result = await importHandoff(document, { schema: handoffSchema });
    const counts = onImportArticles(result.articles);
    setPhase('importado');
    setImportedSummary({
      handoffId: result.handoffId,
      mode: result.mode,
      stories: result.articles.map((a) => ({
        title: a.title,
        revision: 0,
        sources: a.sources.length,
      })),
    });
    const details = [
      `Identificador del traspaso: ${result.handoffId} (${result.mode === 'batch' ? 'lote' : 'noticia individual'}).`,
      `${counts.importedCount} noticia(s) añadida(s) a la redacción con el guion y las fuentes verificados.`,
    ];
    if (counts.duplicateCount > 0) {
      details.push(
        `${counts.duplicateCount} noticia(s) ya estaban en la redacción y no se han duplicado: ${counts.duplicateDetails.join('; ')}`,
      );
    }
    details.push('Las noticias llegan con su revisión aprobada en origen y las fuentes registradas.');
    setFeedback({ kind: 'ok', title: 'Traspaso recibido y verificado', details });
    setPastedJson('');
    setFileContent(null);
    setFileName(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleImport = async () => {
    const raw = fileContent ?? pastedJson.trim();
    if (!raw) {
      setFeedback({
        kind: 'error',
        title: 'No hay ningún traspaso que importar',
        details: ['Selecciona el archivo .json descargado desde neural.news o pega su contenido.'],
      });
      return;
    }
    setIsWorking(true);
    try {
      const document = JSON.parse(raw);
      await acceptDocument(document);
    } catch (err) {
      if (err instanceof DuplicateHandoffError) {
        setPhase('error');
        setFeedback({ kind: 'error', title: 'Traspaso ya recibido', details: [err.message] });
      } else if (err instanceof HandoffValidationError) {
        setPhase('incompatible');
        setFeedback({ kind: 'error', title: 'Traspaso rechazado por no ser válido', details: [err.message] });
      } else if (err instanceof SyntaxError) {
        setFeedback({
          kind: 'error',
          title: 'El archivo no es un JSON legible',
          details: ['Revisa que has pegado o seleccionado el documento de traspaso completo.'],
        });
      } else {
        setPhase('error');
        setFeedback({
          kind: 'error',
          title: 'No se pudo importar el traspaso',
          details: [err instanceof Error ? err.message : String(err)],
        });
      }
    } finally {
      setIsWorking(false);
    }
  };

  return (
    <section className="rounded-lg border border-amber-700/60 bg-slate-900/70 p-4 space-y-3">
      <header className="flex items-center gap-2">
        <span className="material-symbols-outlined text-[20px] text-amber-400">move_to_inbox</span>
        <h2 className="text-sm font-semibold text-amber-200">Traspaso desde neural.news (contrato production_handoff.v1)</h2>
      </header>
      <p className="text-xs text-slate-400">
        Trae las noticias aprobadas desde el motor editorial. El estudio verifica el contrato,
        la integridad del guion aprobado y que no se haya importado antes; las noticias llegan
        marcadas como aprobadas en origen, con sus fuentes.
      </p>

      {deepLinkStory && (
        <div className="rounded border border-sky-800 bg-sky-950/40 p-2 text-[11px] text-sky-200">
          Traspaso solicitado desde neural.news: noticia {deepLinkStory}
          {deepLinkRevision ? ` · revisión ${deepLinkRevision}` : ''}. Se carga automáticamente al abrir.
        </div>
      )}

      <div className="rounded border border-slate-700 bg-slate-950/60 p-3 space-y-2">
        <p className="text-[11px] font-semibold text-slate-300">Vía integrada (recomendada): motor editorial local</p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            className="input !w-auto flex-1"
            inputMode="numeric"
            placeholder="Número de noticia en neural.news (p. ej. 7)"
            value={storyId}
            onChange={(event) => setStoryId(event.target.value)}
            aria-label="Número de noticia en neural.news"
          />
          <button
            type="button"
            onClick={() => void handleFetchFromApi()}
            disabled={fetching}
            className="rounded bg-sky-600 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-sky-500 disabled:opacity-50"
          >
            {fetching ? 'Trayendo…' : 'Traer traspaso del motor'}
          </button>
        </div>
        <p className="text-[11px] text-slate-500">
          Requiere la API local en marcha (127.0.0.1:8000). El motor solo emite traspasos de
          noticias con el guion aprobado; si algo falta, te dirá qué es.
        </p>
      </div>

      <p className="text-[11px] text-slate-500">
        Estado: <span aria-live="polite" className="text-slate-300">{PHASE_LABEL[phase]}</span>
      </p>

      <p className="text-[11px] text-slate-500">…o con un archivo / JSON pegado:</p>
      <div className="flex flex-wrap items-center gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept=".json,application/json"
          onChange={handleFileSelected}
          className="text-xs text-slate-300 file:mr-3 file:rounded file:border-0 file:bg-amber-600 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-slate-950 hover:file:bg-amber-500"
        />
        {fileName && <span className="text-xs text-slate-400">Archivo: {fileName}</span>}
      </div>
      <textarea
        value={pastedJson}
        onChange={(event) => setPastedJson(event.target.value)}
        placeholder="…o pega aquí el contenido del traspaso (JSON)"
        rows={4}
        className="w-full rounded border border-slate-700 bg-slate-950/80 p-2 font-mono text-[11px] text-slate-200 placeholder:text-slate-600 focus:border-amber-600 focus:outline-none"
      />
      <button
        type="button"
        onClick={handleImport}
        disabled={isWorking}
        className="rounded bg-amber-600 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-amber-500 disabled:opacity-50"
      >
        {isWorking ? 'Verificando…' : 'Importar traspaso'}
      </button>

      {importedSummary && (
        <div className="rounded border border-emerald-800 bg-emerald-950/40 p-3 text-xs text-emerald-200">
          <p className="font-semibold">Recibido: {importedSummary.handoffId}</p>
          <ul className="mt-1 space-y-0.5">
            {importedSummary.stories.map((s, idx) => (
              <li key={idx} className="truncate">
                {s.title} · {s.sources} fuente(s)
              </li>
            ))}
          </ul>
          <details className="mt-1">
            <summary className="cursor-pointer text-[11px] text-emerald-300/80">Detalle técnico</summary>
            <pre className="mt-1 overflow-x-auto whitespace-pre-wrap rounded bg-slate-950 p-2 text-[10px] text-emerald-100/80">
              {JSON.stringify(importedSummary, null, 2)}
            </pre>
          </details>
        </div>
      )}

      {feedback && (
        <div
          className={
            feedback.kind === 'ok'
              ? 'rounded border border-emerald-800 bg-emerald-950/70 p-3 text-xs text-emerald-200'
              : 'rounded border border-rose-800 bg-rose-950/70 p-3 text-xs text-rose-200'
          }
        >
          <p className="font-semibold">{feedback.title}</p>
          <ul className="mt-1 list-disc space-y-1 pl-4">
            {feedback.details.map((detail, idx) => (
              <li key={idx}>{detail}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
};
