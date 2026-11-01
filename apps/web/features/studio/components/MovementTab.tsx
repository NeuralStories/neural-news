import React from 'react';
import { CameraMovement } from '../types';

interface MovementTabProps {
  movements: CameraMovement[];
  onToggleMovement: (id: string) => void;
}

export const MovementTab: React.FC<MovementTabProps> = ({
  movements,
  onToggleMovement,
}) => {
  return (
    <div className="space-y-6">
      {/* Cabecera de especificación de 8s */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          Comportamiento Óptico y Dinamismo Visual (duración según proveedor)
        </h3>
        <p className="text-xs text-neutral-400 mt-1 max-w-2xl leading-relaxed">
          Diseñado para tomas de ritmo televisivo vanguardista. Los efectos seleccionados son <strong>estrictamente visuales</strong> y 
          se traducen en el prompt de la toma para mantener la estabilidad de maxDotAi mientras la cámara y el entorno CRT vibran con dinamismo.
        </p>
      </div>

      {/* Lista de movimientos seleccionables */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {movements.map((mov) => {
          return (
            <div
              key={mov.id}
              onClick={() => onToggleMovement(mov.id)}
              className={`p-4 rounded-lg border transition-all cursor-pointer flex items-start gap-3 ${
                mov.selected
                  ? 'bg-neutral-900 border-sky-500 ring-1 ring-sky-500/40 shadow-md shadow-sky-950/20'
                  : 'bg-neutral-900/60 border-neutral-800 hover:border-neutral-700'
              }`}
            >
              <div
                className={`w-5 h-5 rounded flex items-center justify-center mt-0.5 transition ${
                  mov.selected ? 'bg-sky-500 text-neutral-950' : 'border border-neutral-600 bg-neutral-950'
                }`}
              >
                {mov.selected && <span className="text-[14px] font-bold leading-none">✓</span>}
              </div>

              <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white">{mov.label}</span>
                  <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-neutral-950 text-neutral-400 border border-neutral-800">
                    {mov.category}
                  </span>
                </div>
                <p className="text-xs text-neutral-400 leading-relaxed">{mov.description}</p>
                <div className="pt-2 text-[11px] font-mono text-sky-400/90 truncate">
                  Prompt: {mov.promptInstruction}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};