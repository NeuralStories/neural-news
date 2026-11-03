import React, { useState, useRef } from 'react';
import { 
  NewsArticle, 
  ArticleApprovalStatus, 
  VerificationStatus, 
  ProductionEpisodeBlock, 
  VisualReferenceItem, 
  EditorialReferenceItem 
} from '../types';
import { BATCH_5_NEWS_SAMPLE } from '../constants';
import { checkArticleDuplicate, DuplicateMatchResult } from '../utils/newsDeduplication';

interface NewsEditorialTabProps {
  articles: NewsArticle[];
  episodeBlocks: ProductionEpisodeBlock[];
  visualReferences: VisualReferenceItem[];
  editorialReferences: EditorialReferenceItem[];
  onAddArticle: (article: Omit<NewsArticle, 'id' | 'orderIndex'>) => void;
  onImportBatchArticles: (articles: NewsArticle[]) => { importedCount: number; duplicateCount: number; duplicateDetails: string[] };
  onUpdateArticle: (id: string, updates: Partial<NewsArticle>) => void;
  onDeleteArticle: (id: string) => void;
  onSelectArticleForProduction: (article: NewsArticle) => void;
  activeProductionArticleId?: string;
  onAddEpisodeBlock: (title: string, notes?: string) => void;
  onAssignArticleToBlock: (articleId: string, blockTitle: string) => void;
}

export const NewsEditorialTab: React.FC<NewsEditorialTabProps> = ({
  articles,
  episodeBlocks,
  visualReferences,
  editorialReferences,
  onAddArticle,
  onImportBatchArticles,
  onUpdateArticle,
  onDeleteArticle,
  onSelectArticleForProduction,
  activeProductionArticleId,
  onAddEpisodeBlock,
  onAssignArticleToBlock,
}) => {
  const [filterStatus, setFilterStatus] = useState<ArticleApprovalStatus | 'todas'>('todas');
  const [filterBlock, setFilterBlock] = useState<string>('todos');
  const [searchQuery, setSearchQuery] = useState('');

  // Modales
  const [showSingleModal, setShowSingleModal] = useState(false);
  const [showBatchModal, setShowBatchModal] = useState(false);
  const [showBlockModal, setShowBlockModal] = useState(false);

  // Formulario individual
  const [title, setTitle] = useState('');
  const [summary, setSummary] = useState('');
  const [fullScript, setFullScript] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [verificationStatus, setVerificationStatus] = useState<VerificationStatus>('en_revision');
  const [approvalStatus, setApprovalStatus] = useState<ArticleApprovalStatus>('pendiente');
  const [selectedBlock, setSelectedBlock] = useState('Bloque 1: Titulares Principales');
  const [sourcesInput, setSourcesInput] = useState('');
  const [tagsInput, setTagsInput] = useState('');
  const [selectedVisualRefs, setSelectedVisualRefs] = useState<string[]>(['REF-CHAR-01', 'REF-BG-CRT-01']);
  const [selectedEditorialRefs, setSelectedEditorialRefs] = useState<string[]>([]);
  const [formError, setFormError] = useState<string | null>(null);

  // Formulario Lote JSON
  const [batchJsonInput, setBatchJsonInput] = useState('');
  const [batchFeedback, setBatchFeedback] = useState<string | null>(null);
  const [batchDupeList, setBatchDupeList] = useState<string[]>([]);

  // Formulario Nuevo Bloque
  const [newBlockTitle, setNewBlockTitle] = useState('');
  const [newBlockNotes, setNewBlockNotes] = useState('');

  const batchFileInputRef = useRef<HTMLInputElement>(null);

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

  // Guardar noticia individual con chequeo multidimensional de duplicados
  const handleSaveSingle = () => {
    if (!title.trim()) {
      setFormError('Introduce un titular informativo verídico.');
      return;
    }
    if (!fullScript.trim()) {
      setFormError('Introduce el guion editorial de la noticia.');
      return;
    }

    const sources = sourcesInput.split('\n').map(s => s.trim()).filter(s => s.length > 0);
    const tags = tagsInput.split(',').map(t => t.trim().toLowerCase()).filter(t => t.length > 0);

    const candidate: Partial<NewsArticle> = {
      title: title.trim(),
      sources,
      fullScript: fullScript.trim()
    };

    const dupeCheck = checkArticleDuplicate(candidate, articles);
    if (dupeCheck.isDuplicate) {
      setFormError(`Noticia duplicada detectada: ${dupeCheck.details}`);
      return;
    }

    onAddArticle({
      title: title.trim(),
      summary: summary.trim() || title.trim(),
      fullScript: fullScript.trim(),
      date,
      verificationStatus,
      approvalStatus,
      episodeBlock: selectedBlock,
      sources,
      editorialReferenceIds: selectedEditorialRefs,
      visualReferenceIds: selectedVisualRefs,
      tags,
      metadata: {
        importedFrom: 'manual',
        verifiedBy: 'neural.news Redacción Central'
      }
    });

    // Reset
    setTitle('');
    setSummary('');
    setFullScript('');
    setSourcesInput('');
    setTagsInput('');
    setFormError(null);
    setShowSingleModal(false);
  };

  // Procesar lote JSON con detección multidimensional
  const handleProcessBatchJson = (jsonString: string) => {
    try {
      setBatchFeedback(null);
      setBatchDupeList([]);
      const parsed = JSON.parse(jsonString);
      let list: any[] = [];

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

      const res = onImportBatchArticles(formatted);
      setBatchFeedback(`✓ Importadas con éxito: ${res.importedCount} noticias. Descartadas por duplicidad: ${res.duplicateCount}.`);
      setBatchDupeList(res.duplicateDetails);

      if (res.importedCount > 0 && res.duplicateCount === 0) {
        setTimeout(() => {
          setShowBatchModal(false);
          setBatchJsonInput('');
          setBatchFeedback(null);
        }, 2200);
      }
    } catch (err: any) {
      setBatchFeedback(`Error en validación JSON: ${err.message}`);
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
    <div className="space-y-6">
      {/* Cabecera del módulo Editorial neural.news */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[20px] text-amber-400">newspaper</span>
              <h3 className="text-sm font-semibold text-white">
                Módulo Editorial: Redacción y Escaleta neural.news
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Detección Multidimensional Activa
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl leading-relaxed">
              Comprueba fuentes, enlaces de YouTube/Spotify, metadatos y estado de verificación.
              Los duplicados se detectan por <strong>ID, URL de fuente canónica y similitud léxica</strong>.
            </p>
          </div>

          {/* Acciones de importación */}
          <div className="flex flex-wrap items-center gap-2 self-start lg:self-auto">
            <button
              onClick={() => setShowSingleModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded text-xs transition cursor-pointer shadow-md shadow-amber-500/20"
            >
              <span className="material-symbols-outlined text-[16px]">add</span>
              <span>Nueva Noticia</span>
            </button>

            <button
              onClick={() => setShowBatchModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-medium transition cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px] text-amber-400">inventory_2</span>
              <span>Importar Lote (5/10)</span>
            </button>

            <button
              onClick={() => setShowBlockModal(true)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-medium transition cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px]">view_timeline</span>
              <span className="hidden sm:inline">Nuevo Bloque</span>
            </button>
          </div>
        </div>

        {/* Resumen de noticias y escaleta */}
        <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3 text-slate-300">
            <span className="text-slate-500 font-mono">ESTADO DE LA REDACCIÓN:</span>
            <span className="font-bold text-white font-mono">{articles.length}</span>
            <span>noticias totales</span>
            <span className="text-slate-600">|</span>
            <span className="font-bold text-emerald-400 font-mono">
              {articles.filter(a => a.approvalStatus === 'aprobada').length}
            </span>
            <span>aprobadas para vídeo</span>
            <span className="text-slate-600">|</span>
            <span className="font-bold text-amber-400 font-mono">
              {articles.filter(a => a.verificationStatus === 'verificado').length}
            </span>
            <span>verificadas con fuentes</span>
          </div>

          {activeProductionArticleId && (
            <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              <span>Noticia activa en producción audiovisual</span>
            </div>
          )}
        </div>
      </div>

      {/* Barra de Filtros, Búsqueda y Bloques */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1 overflow-x-auto bg-slate-900 p-1 rounded-lg border border-slate-800">
          {(['todas', 'aprobada', 'pendiente', 'descartada'] as const).map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              className={`px-3 py-1 rounded text-xs font-medium capitalize transition cursor-pointer whitespace-nowrap ${
                filterStatus === st
                  ? 'bg-amber-500 text-slate-950 font-bold shadow'
                  : 'text-slate-400 hover:text-white'
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
            className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-amber-500"
          >
            <option value="todos">Todos los Bloques</option>
            {episodeBlocks.map((b) => (
              <option key={b.id} value={b.title}>
                {b.title}
              </option>
            ))}
          </select>

          <div className="relative w-48 sm:w-56">
            <span className="material-symbols-outlined absolute left-2.5 top-1/2 -translate-y-1/2 text-[16px] text-slate-500 pointer-events-none">
              search
            </span>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar noticia, fuentes..."
              className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500"
            />
          </div>
        </div>
      </div>

      {/* Lista de noticias editorial */}
      {filteredArticles.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-10 text-center space-y-3">
          <span className="material-symbols-outlined text-[36px] text-slate-600 block">
            newspaper
          </span>
          <h4 className="text-sm font-semibold text-slate-300">
            No hay noticias con los filtros actuales
          </h4>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Importa un lote de noticias en JSON o añade una noticia individual.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredArticles.map((art) => {
            const isApproved = art.approvalStatus === 'aprobada';
            const isVerified = art.verificationStatus === 'verificado';
            const isActive = art.id === activeProductionArticleId;

            return (
              <div
                key={art.id}
                className={`bg-slate-900 rounded-lg border p-4 transition-all flex flex-col md:flex-row items-start justify-between gap-4 ${
                  isActive
                    ? 'border-amber-500 ring-1 ring-amber-500/50 bg-slate-900/90 shadow-lg shadow-amber-950/20'
                    : isApproved
                    ? 'border-slate-800 hover:border-slate-700'
                    : 'border-slate-800/60 opacity-80'
                }`}
              >
                {/* Lado izquierdo: Metadatos y contenido editorial */}
                <div className="space-y-2 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
                      {art.date}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                      {art.episodeBlock || 'Sin bloque'}
                    </span>
                    <span
                      className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded border ${
                        isVerified
                          ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                          : art.verificationStatus === 'en_revision'
                          ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                          : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                      }`}
                    >
                      {art.verificationStatus.toUpperCase()}
                    </span>
                    {isActive && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500 text-slate-950 font-mono">
                        EN ESTUDIO AUDIOVISUAL
                      </span>
                    )}
                  </div>

                  <h4 className="text-sm font-bold text-white leading-snug">
                    {art.title}
                  </h4>

                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                    {art.summary}
                  </p>

                  <div className="p-2.5 rounded bg-slate-950 border border-slate-800/80 text-xs font-mono text-slate-300">
                    <span className="text-slate-500 block text-[10px] uppercase font-sans mb-0.5">
                      Guion Editorial ({art.fullScript.split(/\s+/).filter(w => w.length > 0).length} palabras):
                    </span>
                    <p className="leading-relaxed line-clamp-2">{art.fullScript}</p>
                  </div>

                  {/* Fuentes e identificadores */}
                  <div className="flex flex-wrap items-center gap-3 pt-1 text-[11px] text-slate-400">
                    {art.sources && art.sources.length > 0 && (
                      <div className="flex items-center gap-1">
                        <span className="material-symbols-outlined text-[14px] text-slate-500">link</span>
                        <span>Fuentes: <strong>{art.sources.length}</strong></span>
                      </div>
                    )}
                    {art.visualReferenceIds && art.visualReferenceIds.length > 0 && (
                      <div className="flex items-center gap-1 font-mono">
                        <span className="material-symbols-outlined text-[14px] text-amber-400">collections</span>
                        <span>Refs visuales: {art.visualReferenceIds.join(', ')}</span>
                      </div>
                    )}
                    {art.editorialReferenceIds && art.editorialReferenceIds.length > 0 && (
                      <div className="flex items-center gap-1 font-mono">
                        <span className="material-symbols-outlined text-[14px] text-cyan-400">menu_book</span>
                        <span>Docs: {art.editorialReferenceIds.join(', ')}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Acciones de aprobación y producción */}
                <div className="flex flex-col sm:flex-row md:flex-col items-end gap-2 w-full md:w-auto pt-2 md:pt-0 border-t md:border-t-0 border-slate-800">
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => onUpdateArticle(art.id, { approvalStatus: 'aprobada' })}
                      className={`px-2 py-1 rounded text-xs font-semibold transition cursor-pointer ${
                        art.approvalStatus === 'aprobada'
                          ? 'bg-emerald-500 text-slate-950 font-bold'
                          : 'bg-slate-800 text-slate-400 hover:text-emerald-300'
                      }`}
                      title="Aprobar para producción audiovisual"
                    >
                      Aprobar ✓
                    </button>
                    <button
                      onClick={() => onUpdateArticle(art.id, { approvalStatus: 'pendiente' })}
                      className={`px-2 py-1 rounded text-xs font-semibold transition cursor-pointer ${
                        art.approvalStatus === 'pendiente'
                          ? 'bg-amber-500 text-slate-950 font-bold'
                          : 'bg-slate-800 text-slate-400 hover:text-amber-300'
                      }`}
                      title="Marcar como pendiente"
                    >
                      Pendiente ⏳
                    </button>
                    <button
                      onClick={() => onUpdateArticle(art.id, { approvalStatus: 'descartada' })}
                      className={`px-2 py-1 rounded text-xs font-semibold transition cursor-pointer ${
                        art.approvalStatus === 'descartada'
                          ? 'bg-rose-500 text-slate-950 font-bold'
                          : 'bg-slate-800 text-slate-400 hover:text-rose-300'
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
                        ? 'opacity-40 cursor-not-allowed bg-slate-800 text-slate-500'
                        : isActive
                        ? 'bg-amber-400 text-slate-950 ring-2 ring-amber-500'
                        : 'bg-amber-500 hover:bg-amber-400 text-slate-950'
                    }`}
                  >
                    <span className="material-symbols-outlined text-[16px]">movie</span>
                    <span>{isActive ? 'Activa en Estudio' : 'Producir en Vídeo'}</span>
                  </button>

                  <button
                    onClick={() => onDeleteArticle(art.id)}
                    className="p-1 text-slate-500 hover:text-rose-400 rounded transition cursor-pointer"
                    title="Eliminar de la redacción"
                  >
                    <span className="material-symbols-outlined text-[16px]">delete</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal: Redacción de Nueva Noticia Individual */}
      {showSingleModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-2xl overflow-y-auto max-h-[92vh]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-amber-400 text-[20px]">post_add</span>
                <h3 className="text-sm font-bold text-white">Redacción de Noticia Editorial</h3>
              </div>
              <button
                onClick={() => setShowSingleModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded cursor-pointer"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded bg-rose-950/80 border border-rose-800 text-rose-200 text-xs flex items-center gap-2">
                <span className="material-symbols-outlined text-[16px] text-rose-400">error</span>
                <span>{formError}</span>
              </div>
            )}

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 font-medium mb-1">Titular Informativo *</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Ej: Análisis de Inferencia en Tiempo Real"
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 font-medium mb-1">Resumen Editorial</label>
                <textarea
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                  rows={2}
                  placeholder="Resumen informativo..."
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-slate-400 font-medium">Guion Editorial Completo *</label>
                  <span className="text-[11px] font-mono text-slate-500">
                    Palabras: {fullScript.split(/\s+/).filter(w => w.length > 0).length}
                  </span>
                </div>
                <textarea
                  value={fullScript}
                  onChange={(e) => setFullScript(e.target.value)}
                  rows={5}
                  placeholder="Escribe el guion completo..."
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2.5 text-slate-200 focus:outline-none focus:border-amber-500 leading-relaxed font-mono"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-400 font-medium mb-1">Fecha</label>
                  <input
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-amber-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-medium mb-1">Verificación de Fuentes</label>
                  <select
                    value={verificationStatus}
                    onChange={(e) => setVerificationStatus(e.target.value as VerificationStatus)}
                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-amber-500"
                  >
                    <option value="verificado">Verificado ✓</option>
                    <option value="en_revision">En Revisión ⏳</option>
                    <option value="sin_verificar">Sin Verificar ⚠</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 font-medium mb-1">Bloque / Episodio</label>
                  <select
                    value={selectedBlock}
                    onChange={(e) => setSelectedBlock(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-amber-500"
                  >
                    {episodeBlocks.map((b) => (
                      <option key={b.id} value={b.title}>
                        {b.title}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-400 font-medium mb-1">Fuentes Originales (URLs)</label>
                <textarea
                  value={sourcesInput}
                  onChange={(e) => setSourcesInput(e.target.value)}
                  rows={2}
                  placeholder="https://ejemplo.com/fuente"
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-amber-500 font-mono text-xs"
                />
              </div>

              <div>
                <label className="block text-slate-400 font-medium mb-1">
                  Referencias Audiovisuales Canónicas:
                </label>
                <div className="flex flex-wrap gap-2 p-2 rounded bg-slate-950 border border-slate-800 max-h-28 overflow-y-auto">
                  {visualReferences.map((vr) => {
                    const isSelected = selectedVisualRefs.includes(vr.identifier);
                    return (
                      <button
                        type="button"
                        key={vr.id}
                        onClick={() => {
                          setSelectedVisualRefs(prev => 
                            isSelected ? prev.filter(x => x !== vr.identifier) : [...prev, vr.identifier]
                          );
                        }}
                        className={`px-2 py-1 rounded text-[11px] font-mono transition cursor-pointer border ${
                          isSelected
                            ? 'bg-amber-500 text-slate-950 font-bold border-amber-400'
                            : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-white'
                        }`}
                      >
                        [{vr.identifier}] {vr.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowSingleModal(false)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs transition cursor-pointer"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleSaveSingle}
                className="px-4 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded text-xs transition cursor-pointer shadow-md shadow-amber-500/20"
              >
                Guardar en Redacción
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Importación de Lotes de Noticias en JSON */}
      {showBatchModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-amber-400 text-[20px]">inventory_2</span>
                <h3 className="text-sm font-bold text-white">Importar Lotes de Noticias JSON</h3>
              </div>
              <button
                onClick={() => setShowBatchModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded cursor-pointer"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Importa paquetes en JSON con validación de fuentes y <strong>detección estricta de duplicados</strong> (por ID, fuente y similitud de titular).
            </p>

            {batchFeedback && (
              <div className={`p-3 rounded text-xs flex items-start gap-2 border ${
                batchFeedback.startsWith('✓') 
                  ? 'bg-emerald-950/80 border-emerald-800 text-emerald-200' 
                  : 'bg-rose-950/80 border-rose-800 text-rose-200'
              }`}>
                <span className="material-symbols-outlined text-[16px] mt-0.5">
                  {batchFeedback.startsWith('✓') ? 'check_circle' : 'error'}
                </span>
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
              <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-slate-400">
                <span>Pega el JSON o sube un archivo:</span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setBatchJsonInput(JSON.stringify(BATCH_5_NEWS_SAMPLE, null, 2))}
                    className="text-amber-400 hover:underline cursor-pointer"
                  >
                    Cargar Lote de Prueba (5 Noticias)
                  </button>
                  <button
                    type="button"
                    onClick={() => batchFileInputRef.current?.click()}
                    className="text-slate-300 hover:text-white underline cursor-pointer"
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
                className="w-full text-xs font-mono bg-slate-950 border border-slate-800 rounded p-3 text-slate-200 focus:outline-none focus:border-amber-500 leading-relaxed"
              />
            </div>

            <div className="pt-2 border-t border-slate-800 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowBatchModal(false)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs transition cursor-pointer"
              >
                Cerrar
              </button>
              <button
                type="button"
                onClick={() => handleProcessBatchJson(batchJsonInput)}
                className="px-4 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded text-xs transition cursor-pointer shadow-md shadow-amber-500/20"
              >
                Procesar e Importar Lote
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Nuevo Bloque o Episodio */}
      {showBlockModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-amber-400 text-[20px]">view_timeline</span>
                <h3 className="text-sm font-bold text-white">Nuevo Bloque / Episodio</h3>
              </div>
              <button
                onClick={() => setShowBlockModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded cursor-pointer"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 font-medium mb-1">Nombre del Bloque *</label>
                <input
                  type="text"
                  value={newBlockTitle}
                  onChange={(e) => setNewBlockTitle(e.target.value)}
                  placeholder="Ej: Episodio 43 - Especial Semiconductores"
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 font-medium mb-1">Notas de Producción</label>
                <textarea
                  value={newBlockNotes}
                  onChange={(e) => setNewBlockNotes(e.target.value)}
                  rows={2}
                  placeholder="Notas de escaleta..."
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-amber-500"
                />
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowBlockModal(false)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs transition cursor-pointer"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => {
                  if (newBlockTitle.trim()) {
                    onAddEpisodeBlock(newBlockTitle.trim(), newBlockNotes.trim());
                    setNewBlockTitle('');
                    setNewBlockNotes('');
                    setShowBlockModal(false);
                  }
                }}
                className="px-4 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded text-xs transition cursor-pointer"
              >
                Crear Bloque
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};