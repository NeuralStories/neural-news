import React, { useRef, useState } from 'react';
import type { ArticleApprovalStatus, NewsArticle, VerificationStatus } from '../../types';
import { BATCH_5_NEWS_SAMPLE } from '../../constants';
import { errorMessage as mensajeDeError } from '../../utils/errorMessage';

/**
 * Modal de importación de lotes de noticias en JSON (NN-113.13).
 *
 * Antes vivía dentro de `NewsEditorialTab.tsx` (759 líneas).
 */

/**
 * Noticia importada de un JSON: admite los nombres en inglés (el contrato del
 * Studio) y los alias en español que llegan de exportaciones antiguas.
 */
type NoticiaImportada = Partial<NewsArticle> & {
  titulo?: string;
  resumen?: string;
  script?: string;
  guion?: string;
  fecha?: string;
  bloque?: string;
  fuentes?: string[];
  externalId?: string;
  metadata?: { externalId?: string; [clave: string]: unknown };
};

export interface ResultadoImportacion {
  importedCount: number;
  duplicateCount: number;
  duplicateDetails: string[];
}

interface ModalImportarLoteProps {
  onImportar: (articles: NewsArticle[]) => ResultadoImportacion;
  onCerrar: () => void;
}

export const ModalImportarLote: React.FC<ModalImportarLoteProps> = ({ onImportar, onCerrar }) => {
  const [batchJsonInput, setBatchJsonInput] = useState('');
  const [batchFeedback, setBatchFeedback] = useState<string | null>(null);
  const [batchDupeList, setBatchDupeList] = useState<string[]>([]);
  const batchFileInputRef = useRef<HTMLInputElement>(null);

  /** Procesa el lote JSON con detección multidimensional de duplicados. */
  const handleProcessBatchJson = (jsonString: string) => {
    try {
      setBatchFeedback(null);
      setBatchDupeList([]);
      const parsed = JSON.parse(jsonString);
      let list: NoticiaImportada[] = [];

      if (Array.isArray(parsed)) {
        list = parsed;
      } else if (Array.isArray(parsed.articles) || Array.isArray(parsed.noticias)) {
        list = parsed.articles || parsed.noticias;
      } else {
        throw new Error('El JSON debe ser un array de noticias o un objeto con la propiedad "articles"');
      }

      const formatted: NewsArticle[] = list.map((item, idx) => ({
        id: item.id || `batch-news-${Date.now()}-${idx}`,
        uuid: item.uuid,
        slug: item.slug,
        title: item.title || item.titulo || 'Sin título',
        summary: item.summary || item.resumen || item.title || '',
        fullScript: item.fullScript || item.script || item.guion || '',
        date: item.date || item.fecha || new Date().toISOString().split('T')[0],
        verificationStatus: (item.verificationStatus as VerificationStatus) || 'sin_verificar',
        approvalStatus: (item.approvalStatus as ArticleApprovalStatus) || 'pendiente',
        episodeBlock: item.episodeBlock || item.bloque || 'Bloque 1: Titulares Principales',
        orderIndex: item.orderIndex || idx + 1,
        sources: Array.isArray(item.sources) ? item.sources : Array.isArray(item.fuentes) ? item.fuentes : [],
        editorialReferenceIds: Array.isArray(item.editorialReferenceIds) ? item.editorialReferenceIds : [],
        visualReferenceIds: Array.isArray(item.visualReferenceIds) ? item.visualReferenceIds : ['REF-CHAR-01', 'REF-BG-CRT-01'],
        tags: Array.isArray(item.tags) ? item.tags : [],
        metadata: {
          importedFrom: 'batch_json',
          externalId: item.externalId || item.metadata?.externalId
        }
      }));

      const res = onImportar(formatted);
      setBatchFeedback(`✓ Importadas con éxito: ${res.importedCount} noticias. Descartadas por duplicidad: ${res.duplicateCount}.`);
      setBatchDupeList(res.duplicateDetails);

      if (res.importedCount > 0 && res.duplicateCount === 0) {
        setTimeout(() => {
          onCerrar();
          setBatchJsonInput('');
          setBatchFeedback(null);
        }, 2200);
      }
    } catch (err) {
      setBatchFeedback(`Error en validación JSON: ${mensajeDeError(err) ?? 'error desconocido'}`);
    }
  };

  const handleBatchFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        setBatchJsonInput(reader.result);
        handleProcessBatchJson(reader.result);
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-2xl">
        <div className="panel-header">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-white">Importar Lotes de Noticias JSON</h3>
          </div>
          <button
            onClick={onCerrar}
            aria-label="Cerrar la ventana de importación de lotes"
            title="Cerrar"
            className="text-neutral-400 hover:text-white p-1 rounded cursor-pointer"
          >
            ✕
          </button>
        </div>

        <p className="text-xs text-neutral-300 leading-relaxed">
          Importa paquetes en JSON con validación de fuentes y <strong>detección estricta de duplicados</strong> (por ID, fuente y similitud de titular).
        </p>

        {batchFeedback && (
          <div className={`p-3 rounded text-xs flex items-start gap-2 border ${
            batchFeedback.startsWith('✓')
              ? 'bg-emerald-950/80 border-emerald-800 text-emerald-200'
              : 'bg-rose-950/80 border-rose-800 text-rose-200'
          }`}>
            <div className="flex-1">
              <span>{batchFeedback}</span>
              {batchDupeList.length > 0 && (
                <ul className="mt-1.5 list-disc list-inside text-[11px] font-mono opacity-90 space-y-0.5">
                  {batchDupeList.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}

        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-neutral-400">
            <span>Pega el JSON o sube un archivo:</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setBatchJsonInput(JSON.stringify(BATCH_5_NEWS_SAMPLE, null, 2))}
                className="text-sky-400 hover:underline cursor-pointer"
              >
                Cargar Lote de Prueba (5 Noticias)
              </button>
              <button
                type="button"
                onClick={() => batchFileInputRef.current?.click()}
                className="text-neutral-300 hover:text-white underline cursor-pointer"
              >
                Subir Archivo .json
              </button>
              <input
                type="file"
                ref={batchFileInputRef}
                onChange={handleBatchFileChange}
                accept=".json,application/json"
                className="hidden"
              />
            </div>
          </div>

          <textarea
            value={batchJsonInput}
            onChange={(e) => setBatchJsonInput(e.target.value)}
            rows={9}
            placeholder="[\n  {\n    'title': 'Titular...',\n    'fullScript': 'Guion completo...',\n    'sources': ['https://...'],\n    'verificationStatus': 'sin_verificar'\n  }\n]"
            className="w-full text-xs font-mono bg-neutral-950 border border-neutral-800 rounded p-3 text-neutral-200 focus:outline-none focus:border-sky-500 leading-relaxed"
          />
        </div>

        <div className="modal-actions">
          <button
            type="button"
            onClick={onCerrar}
            className="px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded text-xs transition cursor-pointer"
          >
            Cerrar
          </button>
          <button
            type="button"
            onClick={() => handleProcessBatchJson(batchJsonInput)}
            className="px-4 py-1.5 bg-sky-500 hover:bg-sky-400 text-neutral-950 font-bold rounded text-xs transition cursor-pointer shadow-md shadow-sky-500/20"
          >
            Procesar e Importar Lote
          </button>
        </div>
      </div>
    </div>
  );
};
