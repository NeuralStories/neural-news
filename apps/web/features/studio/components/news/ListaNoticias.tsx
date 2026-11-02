import React from 'react';
import type { NewsArticle } from '../../types';

/**
 * Lista de noticias de la redacción (NN-113.13).
 *
 * Extraída de `NewsEditorialTab.tsx`, que tenía 759 líneas y mezclaba la
 * cabecera, los filtros, la lista y tres modales.
 */
interface ListaNoticiasProps {
  articulos: NewsArticle[];
  activeProductionArticleId?: string;
  onUpdateArticle: (id: string, updates: Partial<NewsArticle>) => void;
  onDeleteArticle: (id: string) => void;
  onSelectArticleForProduction: (article: NewsArticle) => void;
}

export const ListaNoticias: React.FC<ListaNoticiasProps> = ({
  articulos,
  activeProductionArticleId,
  onUpdateArticle,
  onDeleteArticle,
  onSelectArticleForProduction,
}) => {
  if (articulos.length === 0) {
    return (
      <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-10 text-center space-y-3">
        <h4 className="text-sm font-semibold text-neutral-300">
          No hay noticias con los filtros actuales
        </h4>
        <p className="text-xs text-neutral-500 max-w-sm mx-auto">
          Importa un lote de noticias en JSON o añade una noticia individual.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {articulos.map((art) => {
        const isApproved = art.approvalStatus === 'aprobada';
        const isVerified = art.verificationStatus === 'verificado';
        const isActive = art.id === activeProductionArticleId;

        return (
          <div
            key={art.id}
            className={`bg-neutral-900 rounded-lg border p-4 transition-all flex flex-col md:flex-row items-start justify-between gap-4 ${
              isActive
                ? 'border-sky-500 ring-1 ring-sky-500/50 bg-neutral-900/90 shadow-lg shadow-sky-950/20'
                : isApproved
                ? 'border-neutral-800 hover:border-neutral-700'
                : 'border-neutral-800/60 opacity-80'
            }`}
          >
            {/* Lado izquierdo: Metadatos y contenido editorial */}
            <div className="space-y-2 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-neutral-950 text-neutral-400 border border-neutral-800">
                  {art.date}
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">
                  {art.episodeBlock || 'Sin bloque'}
                </span>
                <span
                  className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded border ${
                    isVerified
                      ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                      : art.verificationStatus === 'en_revision'
                      ? 'bg-sky-500/15 text-sky-300 border-sky-500/30'
                      : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                  }`}
                >
                  {art.verificationStatus.toUpperCase()}
                </span>
                {isActive && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-sky-500 text-neutral-950 font-mono">
                    EN ESTUDIO AUDIOVISUAL
                  </span>
                )}
              </div>

              <h4 className="text-sm font-bold text-white leading-snug">
                {art.title}
              </h4>

              <p className="text-xs text-neutral-400 line-clamp-2 leading-relaxed">
                {art.summary}
              </p>

              <div className="p-2.5 rounded bg-neutral-950 border border-neutral-800/80 text-xs font-mono text-neutral-300">
                <span className="text-neutral-500 block text-[10px] uppercase font-sans mb-0.5">
                  Guion Editorial ({art.fullScript.split(/\s+/).filter(w => w.length > 0).length} palabras):
                </span>
                <p className="leading-relaxed line-clamp-2">{art.fullScript}</p>
              </div>

              {/* Fuentes e identificadores */}
              <div className="flex flex-wrap items-center gap-3 pt-1 text-[11px] text-neutral-400">
                {art.sources && art.sources.length > 0 && (
                  <div className="flex items-center gap-1">
                    <span>Fuentes: <strong>{art.sources.length}</strong></span>
                  </div>
                )}
                {art.visualReferenceIds && art.visualReferenceIds.length > 0 && (
                  <div className="flex items-center gap-1 font-mono">
                    <span>Refs visuales: {art.visualReferenceIds.join(', ')}</span>
                  </div>
                )}
                {art.editorialReferenceIds && art.editorialReferenceIds.length > 0 && (
                  <div className="flex items-center gap-1 font-mono">
                    <span>Docs: {art.editorialReferenceIds.join(', ')}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Acciones de aprobación y producción */}
            <div className="flex flex-col sm:flex-row md:flex-col items-end gap-2 w-full md:w-auto pt-2 md:pt-0 border-t md:border-t-0 border-neutral-800">
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => onUpdateArticle(art.id, { approvalStatus: 'aprobada' })}
                  className={`px-2 py-1 rounded text-xs font-semibold transition cursor-pointer ${
                    art.approvalStatus === 'aprobada'
                      ? 'bg-emerald-500 text-neutral-950 font-bold'
                      : 'bg-neutral-800 text-neutral-400 hover:text-emerald-300'
                  }`}
                  title="Aprobar para producción audiovisual"
                >
                  Aprobar ✓
                </button>
                <button
                  onClick={() => onUpdateArticle(art.id, { approvalStatus: 'pendiente' })}
                  className={`px-2 py-1 rounded text-xs font-semibold transition cursor-pointer ${
                    art.approvalStatus === 'pendiente'
                      ? 'bg-sky-500 text-neutral-950 font-bold'
                      : 'bg-neutral-800 text-neutral-400 hover:text-sky-300'
                  }`}
                  title="Marcar como pendiente"
                >
                  Pendiente ⏳
                </button>
                <button
                  onClick={() => onUpdateArticle(art.id, { approvalStatus: 'descartada' })}
                  className={`px-2 py-1 rounded text-xs font-semibold transition cursor-pointer ${
                    art.approvalStatus === 'descartada'
                      ? 'bg-rose-500 text-neutral-950 font-bold'
                      : 'bg-neutral-800 text-neutral-400 hover:text-rose-300'
                  }`}
                  title="Descartar"
                >
                  ✕
                </button>
              </div>

              <button
                disabled={!isApproved}
                onClick={() => onSelectArticleForProduction(art)}
                className={`w-full sm:w-auto px-3.5 py-1.5 rounded text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer shadow-md ${
                  !isApproved
                    ? 'opacity-40 cursor-not-allowed bg-neutral-800 text-neutral-500'
                    : isActive
                    ? 'bg-sky-400 text-neutral-950 ring-2 ring-sky-500'
                    : 'bg-sky-500 hover:bg-sky-400 text-neutral-950'
                }`}
              >
                <span>{isActive ? 'Activa en Estudio' : 'Producir en Vídeo'}</span>
              </button>

              <button
                onClick={() => onDeleteArticle(art.id)}
                className="p-1 text-neutral-500 hover:text-rose-400 rounded transition cursor-pointer"
                title="Eliminar de la redacción"
              >
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
};
