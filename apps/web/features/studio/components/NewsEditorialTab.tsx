import React, { useState } from 'react';
import {
  NewsArticle,
  ArticleApprovalStatus,
  ProductionEpisodeBlock,
  VisualReferenceItem,
} from '../types';
import { ListaNoticias } from './news/ListaNoticias';
import { ModalImportarLote } from './news/ModalImportarLote';
import { ModalNoticiaIndividual } from './news/ModalNoticiaIndividual';
import { ModalNuevoBloque } from './news/ModalNuevoBloque';

/**
 * Módulo Editorial: redacción y escaleta (NN-113.13).
 *
 * Antes eran 759 líneas con la cabecera, los filtros, la lista y tres modales
 * dentro del mismo fichero. Ahora este componente coordina y cada pieza vive
 * en su fichero:
 *
 *   - `news/ListaNoticias.tsx`        — la lista de noticias;
 *   - `news/ModalNoticiaIndividual.tsx` — redacción de una noticia;
 *   - `news/ModalImportarLote.tsx`     — importación de lotes JSON;
 *   - `news/ModalNuevoBloque.tsx`      — alta de bloque/episodio.
 */
interface NewsEditorialTabProps {
  articles: NewsArticle[];
  episodeBlocks: ProductionEpisodeBlock[];
  visualReferences: VisualReferenceItem[];
  onAddArticle: (article: Omit<NewsArticle, 'id' | 'orderIndex'>) => void;
  onImportBatchArticles: (articles: NewsArticle[]) => { importedCount: number; duplicateCount: number; duplicateDetails: string[] };
  onUpdateArticle: (id: string, updates: Partial<NewsArticle>) => void;
  onDeleteArticle: (id: string) => void;
  onSelectArticleForProduction: (article: NewsArticle) => void;
  activeProductionArticleId?: string;
  onAddEpisodeBlock: (title: string, notes?: string) => void;
}

export const NewsEditorialTab: React.FC<NewsEditorialTabProps> = ({
  articles,
  episodeBlocks,
  visualReferences,
  onAddArticle,
  onImportBatchArticles,
  onUpdateArticle,
  onDeleteArticle,
  onSelectArticleForProduction,
  activeProductionArticleId,
  onAddEpisodeBlock,
}) => {
  const [filterStatus, setFilterStatus] = useState<ArticleApprovalStatus | 'todas'>('todas');
  const [filterBlock, setFilterBlock] = useState<string>('todos');
  const [searchQuery, setSearchQuery] = useState('');

  // Modales
  const [showSingleModal, setShowSingleModal] = useState(false);
  const [showBatchModal, setShowBatchModal] = useState(false);
  const [showBlockModal, setShowBlockModal] = useState(false);

  // Filtros combinados
  const filteredArticles = articles.filter((art) => {
    if (filterStatus !== 'todas' && art.approvalStatus !== filterStatus) return false;
    if (filterBlock !== 'todos' && art.episodeBlock !== filterBlock) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = art.title.toLowerCase().includes(q);
      const matchScript = art.fullScript.toLowerCase().includes(q);
      const matchSummary = art.summary.toLowerCase().includes(q);
      const matchTags = art.tags?.some(t => t.toLowerCase().includes(q)) ?? false;
      return matchTitle || matchScript || matchSummary || matchTags;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Cabecera del módulo Editorial neural.news */}
      <div className="card">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-ink">
                Módulo Editorial: Redacción y Escaleta neural.news
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Detección Multidimensional Activa
              </span>
            </div>
            <p className="text-xs text-neutral-400 mt-1 max-w-3xl leading-relaxed">
              Comprueba fuentes, enlaces de YouTube/Spotify, metadatos y estado de verificación.
              Los duplicados se detectan por <strong>ID, URL de fuente canónica y similitud léxica</strong>.
            </p>
          </div>

          {/* Acciones de importación */}
          <div className="flex flex-wrap items-center gap-2 self-start lg:self-auto">
            <button
              onClick={() => setShowSingleModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-sky-500 hover:bg-sky-400 text-neutral-950 font-bold rounded text-xs transition cursor-pointer shadow-md shadow-sky-500/20"
            >
              <span>Nueva Noticia</span>
            </button>

            <button
              onClick={() => setShowBatchModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 border border-neutral-700 rounded text-xs font-medium transition cursor-pointer"
            >
              <span>Importar Lote (5/10)</span>
            </button>

            <button
              onClick={() => setShowBlockModal(true)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 border border-neutral-700 rounded text-xs font-medium transition cursor-pointer"
            >
              <span className="hidden sm:inline">Nuevo Bloque</span>
            </button>
          </div>
        </div>

        {/* Resumen de noticias y escaleta */}
        <div className="mt-4 pt-3 border-t border-neutral-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3 text-neutral-300">
            <span className="text-neutral-500 font-mono">ESTADO DE LA REDACCIÓN:</span>
            <span className="font-bold text-ink font-mono">{articles.length}</span>
            <span>noticias totales</span>
            <span className="text-neutral-600">|</span>
            <span className="font-bold text-emerald-400 font-mono">
              {articles.filter(a => a.approvalStatus === 'aprobada').length}
            </span>
            <span>aprobadas para vídeo</span>
            <span className="text-neutral-600">|</span>
            <span className="font-bold text-sky-400 font-mono">
              {articles.filter(a => a.verificationStatus === 'verificado').length}
            </span>
            <span>verificadas con fuentes</span>
          </div>

          {activeProductionArticleId && (
            <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-sky-500/10 border border-sky-500/30 text-sky-300 text-xs">
              <span className="w-2 h-2 rounded-full bg-sky-400 animate-pulse" />
              <span>Noticia activa en producción audiovisual</span>
            </div>
          )}
        </div>
      </div>

      {/* Barra de Filtros, Búsqueda y Bloques */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1 overflow-x-auto bg-neutral-900 p-1 rounded-md border border-neutral-800">
          {(['todas', 'aprobada', 'pendiente', 'descartada'] as const).map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              className={`px-3 py-1 rounded text-xs font-medium capitalize transition cursor-pointer whitespace-nowrap ${
                filterStatus === st
                  ? 'bg-sky-500 text-neutral-950 font-bold shadow'
                  : 'text-neutral-400 hover:text-ink'
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <select
            value={filterBlock}
            onChange={(e) => setFilterBlock(e.target.value)}
            className="bg-neutral-900 border border-neutral-800 rounded-md px-2.5 py-1.5 text-xs text-neutral-300 focus:outline-none focus:border-sky-500"
          >
            <option value="todos">Todos los Bloques</option>
            {episodeBlocks.map((b) => (
              <option key={b.id} value={b.title}>
                {b.title}
              </option>
            ))}
          </select>

          <div className="relative w-48 sm:w-56">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar noticia, fuentes..."
              className="w-full bg-neutral-900 border border-neutral-800 rounded-md pl-8 pr-3 py-1.5 text-xs text-neutral-200 placeholder-neutral-500 focus:outline-none focus:border-sky-500"
            />
          </div>
        </div>
      </div>

      {/* Lista de noticias editorial */}
      <ListaNoticias
        articulos={filteredArticles}
        activeProductionArticleId={activeProductionArticleId}
        onUpdateArticle={onUpdateArticle}
        onDeleteArticle={onDeleteArticle}
        onSelectArticleForProduction={onSelectArticleForProduction}
      />

      {/* Modal: Redacción de Nueva Noticia Individual */}
      {showSingleModal && (
        <ModalNoticiaIndividual
          articles={articles}
          episodeBlocks={episodeBlocks}
          visualReferences={visualReferences}
          onGuardar={onAddArticle}
          onCerrar={() => setShowSingleModal(false)}
        />
      )}

      {/* Modal: Importación de Lotes de Noticias en JSON */}
      {showBatchModal && (
        <ModalImportarLote
          onImportar={onImportBatchArticles}
          onCerrar={() => setShowBatchModal(false)}
        />
      )}

      {/* Modal: Nuevo Bloque o Episodio */}
      {showBlockModal && (
        <ModalNuevoBloque
          onCrear={onAddEpisodeBlock}
          onCerrar={() => setShowBlockModal(false)}
        />
      )}
    </div>
  );
};
