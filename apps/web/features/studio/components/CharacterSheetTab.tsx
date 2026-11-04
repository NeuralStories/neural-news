import React, { useState } from 'react';
import { MasterSheetState } from '../types';
import { MAXDOTAI_CANONICAL, DEFAULT_MASTER_SHEET_PROMPT } from '../constants';

interface CharacterSheetTabProps {
  sheetState: MasterSheetState;
  onUpdateSheet: (sheet: Partial<MasterSheetState>) => void;
  onSelectExistingMedia: () => Promise<void>;
  onGenerateSheet: (prompt: string) => Promise<void>;
  isGenerating: boolean;
}

export const CharacterSheetTab: React.FC<CharacterSheetTabProps> = ({
  sheetState,
  onUpdateSheet,
  onSelectExistingMedia,
  onGenerateSheet,
  isGenerating,
}) => {
  const [promptText, setPromptText] = useState(DEFAULT_MASTER_SHEET_PROMPT);
  const [copyFeedback, setCopyFeedback] = useState(false);

  const handleCopyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(promptText);
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 2000);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      {/* Banner de regla estricta de identidad */}
      <div className="bg-neutral-900/90 border border-neutral-800 rounded-md p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 mt-0.5">
            </div>
          <div>
            <h3 className="text-sm font-semibold text-ink flex items-center gap-2">
              Identidad Canónica: {MAXDOTAI_CANONICAL.name} ({MAXDOTAI_CANONICAL.handle})
              <span className="text-[10px] font-normal px-2 py-0.5 rounded-full bg-neutral-800 text-neutral-300 border border-neutral-700">
                Regla inmutable
              </span>
            </h3>
            <p className="text-xs text-neutral-400 mt-1 max-w-2xl leading-relaxed">
              No se debe alterar el rostro, gafas rectangulares oscuras, pelo castaño, barba recortada ni vestuario corporativo. 
              La hoja maestra aprobada es la <strong>única referencia admisible</strong> para mantener la consistencia en todas las tomas.
            </p>
          </div>
        </div>

        {/* Acciones principales de importación / selección */}
        <div className="flex items-center gap-2 w-full md:w-auto">
          <button
            onClick={onSelectExistingMedia}
            className="flex-1 md:flex-initial flex items-center justify-center gap-2 px-3.5 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-100 rounded-md text-xs font-medium border border-neutral-700 transition cursor-pointer"
          >
            <span>Seleccionar hoja aprobada</span>
          </button>
        </div>
      </div>

      {/* Visor de Hoja Maestra y Estado de Aprobación */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-neutral-200 uppercase tracking-wider">
                Hoja de Personaje Maestra (16:9)
              </span>
              <span className="text-[11px] font-mono text-neutral-400">
                Exactamente 3 paneles • 1 sola cara frontal
              </span>
            </div>
            {sheetState.base64 && (
              <button
                onClick={() => onUpdateSheet({ isApproved: !sheetState.isApproved })}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition cursor-pointer ${
                  sheetState.isApproved
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    : 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                }`}
              >
                <span>{sheetState.isApproved ? 'Hoja Oficial Aprobada' : 'Marcar como Aprobada'}</span>
              </button>
            )}
          </div>

          <div className="aspect-video w-full rounded-md border-2 border-neutral-800 bg-neutral-950 overflow-hidden relative flex items-center justify-center group shadow-inner">
            {sheetState.base64 ? (
              // eslint-disable-next-line @next/next/no-img-element -- la hoja es un data URL en base64; next/image no lo admite.
              <img
                src={`data:${sheetState.mimeType || 'image/jpeg'};base64,${sheetState.base64}`}
                alt="Hoja de personaje maxDotAi"
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="text-center p-6 max-w-md">
                <div className="w-12 h-12 mx-auto rounded-full bg-neutral-900 border border-neutral-800 flex items-center justify-center text-neutral-500 mb-3">
                  </div>
                <p className="text-sm font-medium text-neutral-300">Sin hoja maestra activa</p>
                <p className="text-xs text-neutral-500 mt-1">
                  Selecciona una hoja de personaje ya aprobada desde la galería o genera una nueva cumpliendo los tres paneles canónicos.
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  <button
                    onClick={onSelectExistingMedia}
                    className="px-3 py-1.5 bg-sky-500 hover:bg-sky-400 text-neutral-950 font-semibold text-xs rounded transition cursor-pointer"
                  >
                    Abrir desde Galería Flow
                  </button>
                </div>
              </div>
            )}

            {/* Overlay informativo de paneles requeridos */}
            <div className="absolute bottom-2 left-2 right-2 pointer-events-none flex justify-between gap-1 text-[10px] font-mono text-neutral-400 bg-neutral-950/80 backdrop-blur px-2.5 py-1 rounded border border-neutral-800/80">
              <span className="truncate">Panel 1: Retrato Frontal (única cara)</span>
              <span className="hidden sm:inline">|</span>
              <span className="truncate">Panel 2: Clavículas Abajo</span>
              <span className="hidden sm:inline">|</span>
              <span className="truncate">Panel 3: Cuerpo Posterior</span>
            </div>
          </div>
        </div>

        {/* Panel lateral de ficha técnica y generador */}
        <div className="lg:col-span-4 space-y-4">
          <div className="card space-y-3">
            <h4 className="text-xs font-semibold text-neutral-200 uppercase tracking-wider flex items-center gap-1.5">
              Ficha Canónica
            </h4>
            <div className="space-y-2 text-xs">
              <div className="inset">
                <span className="text-neutral-500 block text-[10px] uppercase font-mono">Gafas y Mirada</span>
                <span className="text-neutral-200">{MAXDOTAI_CANONICAL.features.glasses}</span>
              </div>
              <div className="inset">
                <span className="text-neutral-500 block text-[10px] uppercase font-mono">Cabello y Barba</span>
                <span className="text-neutral-200">{MAXDOTAI_CANONICAL.features.hair} • {MAXDOTAI_CANONICAL.features.beard}</span>
              </div>
              <div className="inset">
                <span className="text-neutral-500 block text-[10px] uppercase font-mono">Vestuario</span>
                <span className="text-neutral-200">{MAXDOTAI_CANONICAL.features.wardrobe}</span>
              </div>
            </div>
          </div>

          {/* Generador de Hoja con Nano Banana Pro */}
          <div className="card space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-neutral-200 uppercase tracking-wider">
                Generar Nueva Hoja (16:9)
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-400">
                Nano Banana Pro
              </span>
            </div>
            <p className="text-[11px] text-neutral-400">
              Usa este prompt optimizado para producir exactamente la estructura de tres paneles sobre fondo gris.
            </p>
            <textarea
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
              rows={4}
              className="w-full text-xs font-mono bg-neutral-950 border border-neutral-800 rounded p-2 text-neutral-200 focus:outline-none focus:border-sky-500"
            />
            <div className="flex items-center gap-2 pt-1">
              <button
                onClick={handleCopyPrompt}
                className="px-2.5 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 rounded text-xs flex items-center gap-1 transition cursor-pointer"
              >
                <span>{copyFeedback ? 'Copiado' : 'Copiar'}</span>
              </button>
              <button
                disabled={isGenerating}
                onClick={() => onGenerateSheet(promptText)}
                className="flex-1 px-3 py-1.5 bg-sky-500 hover:bg-sky-400 disabled:opacity-50 text-neutral-950 font-bold rounded text-xs flex items-center justify-center gap-1.5 transition cursor-pointer shadow-md shadow-sky-500/20"
              >
                <span>{isGenerating ? 'Generando hoja...' : 'Generar Hoja Maestra'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};