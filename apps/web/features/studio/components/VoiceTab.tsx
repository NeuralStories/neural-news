import React from 'react';
import { VoiceConfig } from '../types';

interface VoiceTabProps {
  voiceConfig: VoiceConfig;
  onUpdateSpeed: (speed: number) => void;
}

export const VoiceTab: React.FC<VoiceTabProps> = ({
  voiceConfig,
  onUpdateSpeed,
}) => {
  return (
    <div className="space-y-6">
      {/* Declaración de capacidad real */}
      <div className="p-4 rounded-md bg-sky-500/10 border border-sky-500/30 text-sky-300 flex items-start gap-3">
        <div className="text-xs space-y-1">
          <p className="font-semibold text-sky-200">
            Aviso de Transparencia de Capacidades
          </p>
          <p className="text-sky-300/90 leading-relaxed">
            Esta sección <strong>prepara la ficha técnica y directrices de locución</strong> para la voz de maxDotAi. 
            El modelo de vídeo actual genera tomas visuales de 8 segundos. No se simula ni se genera audio falso si el motor de síntesis de voz no está acoplado.
          </p>
        </div>
      </div>

      {/* Ficha canónica de voz: Perfil Algenib */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-neutral-900 border border-neutral-800 rounded-md p-5 space-y-4">
          <div className="panel-header">
            <div className="flex items-center gap-2">
              <div>
                <h3 className="text-sm font-bold text-ink">Perfil Preferido: {voiceConfig.profile}</h3>
                <span className="text-[11px] text-neutral-400">Locutor Oficial de NeuralStories News</span>
              </div>
            </div>
            <span className="px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30 text-xs font-mono font-semibold">
              OFICIAL
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <span className="text-neutral-500 block text-[10px] uppercase font-mono">Género y Timbre</span>
              <p className="text-neutral-200 font-medium mt-0.5">{voiceConfig.timbre}</p>
            </div>
            <div>
              <span className="text-neutral-500 block text-[10px] uppercase font-mono">Variante Lingüística</span>
              <p className="text-neutral-200 font-medium mt-0.5">{voiceConfig.locale}</p>
            </div>
            <div>
              <span className="text-neutral-500 block text-[10px] uppercase font-mono">Cadencia y Dinamismo</span>
              <p className="text-neutral-300 leading-relaxed mt-0.5">{voiceConfig.cadenceDescription}</p>
            </div>
          </div>
        </div>

        {/* Ajuste de velocidad y control de ritmo */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-md p-5 space-y-4 flex flex-col justify-between">
          <div>
            <h4 className="text-xs font-semibold text-neutral-200 uppercase tracking-wider mb-2">
              Control de Ritmo de Locución
            </h4>
            <p className="text-xs text-neutral-400 mb-4 leading-relaxed">
              El estilo de NeuralStories exige un ritmo un <strong>15% a 20% más rápido</strong> que la lectura estándar para aportar frescura y densidad informativa.
            </p>

            <div className="space-y-3 bg-neutral-950 p-4 rounded-md border border-neutral-800">
              <div className="flex items-center justify-between text-xs">
                <span className="text-neutral-400">Multiplicador de velocidad:</span>
                <span className="font-mono font-bold text-sky-400">
                  {voiceConfig.speedMultiplier.toFixed(2)}x (+{Math.round((voiceConfig.speedMultiplier - 1) * 100)}%)
                </span>
              </div>

              <input
                type="range"
                min="1.0"
                max="1.3"
                step="0.01"
                value={voiceConfig.speedMultiplier}
                onChange={(e) => onUpdateSpeed(parseFloat(e.target.value))}
                className="w-full accent-sky-500 cursor-pointer"
              />

              <div className="flex justify-between text-[10px] font-mono text-neutral-500">
                <span>1.0x (Estándar)</span>
                <span className="text-sky-400">1.18x (hipótesis Algenib, sin calibrar)</span>
                <span>1.30x (Ultrarrápido)</span>
              </div>
            </div>
          </div>

          <div className="p-3 rounded bg-neutral-950 border border-neutral-800/80 text-[11px] text-neutral-400 font-mono">
            Directiva de modulación: Audio continuo, sin titubeos, dicción limpia, final de frase asertivo.
          </div>
        </div>
      </div>
    </div>
  );
};