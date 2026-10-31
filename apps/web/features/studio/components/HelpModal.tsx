import React from 'react';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HelpModal: React.FC<HelpModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-2xl overflow-y-auto max-h-[90vh]">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <span className="w-7 h-7 rounded bg-amber-500 flex items-center justify-center text-slate-950 font-black text-sm">
              N•
            </span>
            <h2 className="text-base font-bold text-white">Contrato de Datos y Manual neural.news</h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition cursor-pointer"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        <div className="space-y-4 text-xs text-slate-300 leading-relaxed">
          <section className="space-y-1.5">
            <h4 className="font-bold text-amber-400 uppercase tracking-wider text-[11px]">
              1. Sistema Editorial neural.news
            </h4>
            <p>
              Diseñado para ingestión continua individual o en lotes de 5 y 10 noticias. Integra título, resumen, guion completo, fecha, fuentes y estado de verificación estricto. Evita duplicados comparando títulos normalizados.
            </p>
          </section>

          <section className="space-y-1.5">
            <h4 className="font-bold text-amber-400 uppercase tracking-wider text-[11px]">
              2. Desglose de Guion en Escenas (duración calculada por palabras)
            </h4>
            <p>
              El guion editorial completo (30s, 45s, 60s) se divide inteligentemente respetando pausas oracionales en tomas de ~8 segundos (~20-24 palabras a cadencia Algenib de 2.85 palabras/segundo). La locución se mantiene continua sin palabras repetidas ni silencios artificiales.
            </p>
          </section>

          <section className="space-y-1.5">
            <h4 className="font-bold text-amber-400 uppercase tracking-wider text-[11px]">
              3. Biblioteca Dual de Referencias
            </h4>
            <p>
              - <strong>Referencias Editoriales:</strong> Fuentes comprobadas, documentos técnicos y transcripciones de YouTube/Spotify.<br />
              - <strong>Referencias Audiovisuales:</strong> Hoja de tres paneles del presentador @neuraldotai, plató CRT original y estilos de cámara.<br />
              Las referencias aprobadas pueden fijarse como <em>permanentes</em> en cada episodio.
            </p>
          </section>

          <section className="space-y-1.5">
            <h4 className="font-bold text-amber-400 uppercase tracking-wider text-[11px]">
              4. Contrato de Integración JSON (v2.0)
            </h4>
            <div className="bg-slate-950 p-2.5 rounded border border-slate-800 font-mono text-[10px] text-slate-300 space-y-1">
              <p><code>formatVersion: "2.0"</code></p>
              <p><code>articles: [NewsArticle...]</code> (con fuentes y verificación)</p>
              <p><code>visualReferences: [VisualReferenceItem...]</code></p>
              <p><code>editorialReferences: [EditorialReferenceItem...]</code></p>
              <p><code>episodeBlocks: [ProductionEpisodeBlock...]</code></p>
            </div>
          </section>
        </div>

        <div className="pt-3 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded transition cursor-pointer"
          >
            Entendido, volver al estudio
          </button>
        </div>
      </div>
    </div>
  );
};