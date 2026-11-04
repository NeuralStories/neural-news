import React, { useState } from 'react';
import type {
  ArticleApprovalStatus,
  NewsArticle,
  ProductionEpisodeBlock,
  VerificationStatus,
  VisualReferenceItem,
} from '../../types';
import { checkArticleDuplicate } from '../../utils/newsDeduplication';
import { IconoCruce } from '@/components/ui/icono';

/**
 * Modal de redacción de una noticia individual (NN-113.13).
 *
 * Antes vivía dentro de `NewsEditorialTab.tsx` (759 líneas). El modal es
 * autónomo: guarda su propio formulario y avisa al padre sólo cuando la
 * noticia está lista.
 */
interface ModalNoticiaIndividualProps {
  articles: NewsArticle[];
  episodeBlocks: ProductionEpisodeBlock[];
  visualReferences: VisualReferenceItem[];
  onGuardar: (article: Omit<NewsArticle, 'id' | 'orderIndex'>) => void;
  onCerrar: () => void;
}

export const ModalNoticiaIndividual: React.FC<ModalNoticiaIndividualProps> = ({
  articles,
  episodeBlocks,
  visualReferences,
  onGuardar,
  onCerrar,
}) => {
  const [title, setTitle] = useState('');
  const [summary, setSummary] = useState('');
  const [fullScript, setFullScript] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [verificationStatus, setVerificationStatus] = useState<VerificationStatus>('en_revision');
  const [approvalStatus] = useState<ArticleApprovalStatus>('pendiente');
  const [selectedBlock, setSelectedBlock] = useState('Bloque 1: Titulares Principales');
  const [sourcesInput, setSourcesInput] = useState('');
  const [selectedVisualRefs, setSelectedVisualRefs] = useState<string[]>(['REF-CHAR-01', 'REF-BG-CRT-01']);
  const [selectedEditorialRefs] = useState<string[]>([]);
  const [formError, setFormError] = useState<string | null>(null);

  /** Guarda la noticia con chequeo multidimensional de duplicados. */
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
    // El formulario individual **no tiene campo de etiquetas**: el estado que
    // las recogía era inalcanzable (código muerto) y por eso toda noticia creada
    // a mano salía sin etiquetas. Ahora se dice explícitamente.
    const tags: string[] = [];

    const candidate: Partial<NewsArticle> = {
      title: title.trim(),
      sources,
      fullScript: fullScript.trim(),
    };

    const dupeCheck = checkArticleDuplicate(candidate, articles);
    if (dupeCheck.isDuplicate) {
      setFormError(`Noticia duplicada detectada: ${dupeCheck.details}`);
      return;
    }

    onGuardar({
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
    setFormError(null);
    onCerrar();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-neutral-900 border border-neutral-800 rounded-md max-w-2xl w-full p-6 space-y-4 shadow-2xl overflow-y-auto max-h-[92vh]">
        <div className="panel-header">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-ink">Redacción de Noticia Editorial</h3>
          </div>
          <button
            onClick={onCerrar}
            aria-label="Cerrar la ventana de redacción de noticia"
            title="Cerrar"
            className="text-neutral-400 hover:text-ink p-1 rounded cursor-pointer"
          >
            <IconoCruce />
          </button>
        </div>

        {formError && (
          <div className="p-3 rounded bg-rose-950/80 border border-rose-800 text-rose-200 text-xs flex items-center gap-2">
            <span>{formError}</span>
          </div>
        )}

        <div className="space-y-3 text-xs">
          <div>
            <label className="block text-neutral-400 font-medium mb-1">Titular Informativo *</label>
            <input aria-label="Titular Informativo *"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ej: Análisis de Inferencia en Tiempo Real"
              className="input-compact"
            />
          </div>

          <div>
            <label className="block text-neutral-400 font-medium mb-1">Resumen Editorial</label>
            <textarea aria-label="Resumen Editorial"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              rows={2}
              placeholder="Resumen informativo..."
              className="input-compact"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-neutral-400 font-medium">Guion Editorial Completo *</label>
              <span className="text-[11px] font-mono text-neutral-500">
                Palabras: {fullScript.split(/\s+/).filter(w => w.length > 0).length}
              </span>
            </div>
            <textarea aria-label="Guion Editorial Completo *"
              value={fullScript}
              onChange={(e) => setFullScript(e.target.value)}
              rows={5}
              placeholder="Escribe el guion completo..."
              className="w-full bg-neutral-950 border border-neutral-800 rounded p-2.5 text-neutral-200 focus:outline-none focus:border-sky-500 leading-relaxed font-mono"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-neutral-400 font-medium mb-1">Fecha</label>
              <input aria-label="Fecha"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full bg-neutral-950 border border-neutral-800 rounded p-2 text-neutral-200 focus:outline-none focus:border-sky-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-neutral-400 font-medium mb-1">Verificación de Fuentes</label>
              <select aria-label="Verificación de Fuentes"
                value={verificationStatus}
                onChange={(e) => setVerificationStatus(e.target.value as VerificationStatus)}
                className="input-compact"
              >
                <option value="verificado">Verificado</option>
                <option value="en_revision">En Revisión</option>
                <option value="sin_verificar">Sin Verificar</option>
              </select>
            </div>

            <div>
              <label className="block text-neutral-400 font-medium mb-1">Bloque / Episodio</label>
              <select aria-label="Bloque / Episodio"
                value={selectedBlock}
                onChange={(e) => setSelectedBlock(e.target.value)}
                className="input-compact"
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
            <label className="block text-neutral-400 font-medium mb-1">Fuentes Originales (URLs)</label>
            <textarea aria-label="Fuentes Originales (URLs)"
              value={sourcesInput}
              onChange={(e) => setSourcesInput(e.target.value)}
              rows={2}
              placeholder="https://ejemplo.com/fuente"
              className="w-full bg-neutral-950 border border-neutral-800 rounded p-2 text-neutral-200 focus:outline-none focus:border-sky-500 font-mono text-xs"
            />
          </div>

          <div>
            <label className="block text-neutral-400 font-medium mb-1">
              Referencias Audiovisuales Canónicas:
            </label>
            <div className="flex flex-wrap gap-2 p-2 rounded bg-neutral-950 border border-neutral-800 max-h-28 overflow-y-auto">
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
                        ? 'bg-sky-500 text-neutral-950 font-bold border-sky-400'
                        : 'bg-neutral-900 text-neutral-400 border-neutral-800 hover:text-ink'
                    }`}
                  >
                    [{vr.identifier}] {vr.name}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className="pt-3 border-t border-neutral-800 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCerrar}
            className="px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded text-xs transition cursor-pointer"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleSaveSingle}
            className="px-4 py-1.5 bg-sky-500 hover:bg-sky-400 text-neutral-950 font-bold rounded text-xs transition cursor-pointer shadow-md shadow-sky-500/20"
          >
            Guardar en Redacción
          </button>
        </div>
      </div>
    </div>
  );
};
