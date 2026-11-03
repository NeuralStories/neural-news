import React from 'react';
import { BackgroundPreset } from '../types';
import { BACKGROUND_PRESETS } from '../constants';

interface BackgroundTabProps {
  selectedPresetId: string;
  onSelectPreset: (preset: BackgroundPreset) => void;
  aspectRatio: '16:9' | '9:16';
  onChangeAspectRatio: (ratio: '16:9' | '9:16') => void;
  customReferenceMediaId?: string;
  onSelectCustomBackground: () => Promise<void>;
}

export const BackgroundTab: React.FC<BackgroundTabProps> = ({
  selectedPresetId,
  onSelectPreset,
  aspectRatio,
  onChangeAspectRatio,
  customReferenceMediaId,
  onSelectCustomBackground,
}) => {
  return (
    <div className="space-y-6">
      {/* Cabecera explicativa */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px] text-amber-400">tv</span>
              Escenario Físico: Plató de Monitores CRT
            </h3>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
              Conserva el diseño físico de los televisores catódicos con líneas de barrido y fósforo ámbar/cian. 
              El encuadre siempre se formula cerrado desde el pecho para mantener el impacto visual periodístico.
            </p>
          </div>

          {/* Selector de relación de aspecto */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-md border border-slate-800 self-start sm:self-auto">
            <button
              onClick={() => onChangeAspectRatio('16:9')}
              className={`px-3 py-1 rounded text-xs font-mono font-medium transition cursor-pointer flex items-center gap-1 ${
                aspectRatio === '16:9'
                  ? 'bg-amber-500 text-slate-950 font-bold shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <span className="material-symbols-outlined text-[14px]">desktop_windows</span>
              16:9 Horizontal
            </button>
            <button
              onClick={() => onChangeAspectRatio('9:16')}
              className={`px-3 py-1 rounded text-xs font-mono font-medium transition cursor-pointer flex items-center gap-1 ${
                aspectRatio === '9:16'
                  ? 'bg-amber-500 text-slate-950 font-bold shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <span className="material-symbols-outlined text-[14px]">smartphone</span>
              9:16 Vertical
            </button>
          </div>
        </div>
      </div>

      {/* Galería de variantes del escenario CRT */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {BACKGROUND_PRESETS.map((preset) => {
          const isSelected = selectedPresetId === preset.id;
          return (
            <div
              key={preset.id}
              onClick={() => onSelectPreset(preset)}
              className={`rounded-lg border p-4 bg-slate-900 transition-all cursor-pointer flex flex-col justify-between ${
                isSelected
                  ? 'border-amber-500 ring-1 ring-amber-500/50 shadow-lg shadow-amber-950/20'
                  : 'border-slate-800 hover:border-slate-700 hover:bg-slate-850'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-white">{preset.title}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-950 text-amber-400 border border-slate-800">
                    {preset.aspectRatio}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mb-3 leading-relaxed">{preset.description}</p>
                
                {/* Visualización conceptual CRT */}
                <div className="h-28 rounded bg-slate-950 border border-slate-800 relative overflow-hidden flex items-center justify-center p-3">
                  <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:8px_8px] opacity-40" />
                  <div className="absolute inset-x-0 h-0.5 bg-amber-500/20 top-1/2 animate-pulse" />
                  <div className="text-center z-10">
                    <span className="material-symbols-outlined text-amber-400/80 text-[28px]">live_tv</span>
                    <span className="block text-[10px] font-mono text-slate-400 mt-1">CRT BROADCAST MATRIX</span>
                  </div>
                </div>
              </div>

              <div className="pt-3 mt-3 border-t border-slate-800/60 flex items-center justify-between">
                <span className="text-[11px] text-slate-500 font-mono">Encuadre cerrado pecho</span>
                <span className={`text-xs font-semibold ${isSelected ? 'text-amber-400' : 'text-slate-400'}`}>
                  {isSelected ? '✓ Seleccionado' : 'Elegir'}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Opción de vincular imagen de fondo aprobada previamente */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-slate-800 text-slate-300">
            <span className="material-symbols-outlined text-[20px]">add_photo_alternate</span>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-white">¿Tienes un fotograma de plató CRT ya renderizado?</h4>
            <p className="text-xs text-slate-400">
              {customReferenceMediaId
                ? 'Fondo de referencia importado y vinculado para el renderizado.'
                : 'Puedes seleccionarlo desde tu galería para usarlo como referencia visual en Omni 1.1 Flash.'}
            </p>
          </div>
        </div>

        <button
          onClick={onSelectCustomBackground}
          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-medium transition cursor-pointer"
        >
          {customReferenceMediaId ? 'Cambiar referencia de fondo' : 'Seleccionar fondo de galería'}
        </button>
      </div>
    </div>
  );
};