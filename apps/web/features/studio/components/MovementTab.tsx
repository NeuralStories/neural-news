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
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px] text-amber-400">videocam</span>
          Comportamiento Óptico y Dinamismo Visual (duración según proveedor)
        </h3>
        <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
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
                  ? 'bg-slate-900 border-amber-500 ring-1 ring-amber-500/40 shadow-md shadow-amber-950/20'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div
                className={`w-5 h-5 rounded flex items-center justify-center mt-0.5 transition ${
                  mov.selected ? 'bg-amber-500 text-slate-950' : 'border border-slate-600 bg-slate-950'
                }`}
              >
                {mov.selected && (
                  <span className="material-symbols-outlined text-[16px] font-bold">check</span>
                )}
              </div>

              <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white">{mov.label}</span>
                  <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
                    {mov.category}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">{mov.description}</p>
                <div className="pt-2 text-[11px] font-mono text-amber-400/90 truncate">
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