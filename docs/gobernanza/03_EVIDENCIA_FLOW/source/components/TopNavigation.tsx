import React from 'react';
import { StudioTab } from '../types';

interface TopNavigationProps {
  currentTab: StudioTab;
  onSelectTab: (tab: StudioTab) => void;
  hasApprovedSheet: boolean;
  selectedReferencesCount: number;
  approvedNewsCount: number;
  onOpenHelp: () => void;
  onOpenBackupModal?: () => void;
}

const TABS: { id: StudioTab; label: string; icon: string; badge?: string }[] = [
  { id: 'noticias', label: '1. Noticias', icon: 'newspaper' },
  { id: 'personaje', label: '2. Personaje', icon: 'badge' },
  { id: 'fondo', label: '3. Fondo CRT', icon: 'tv' },
  { id: 'guion', label: '4. Guion & Escenas', icon: 'article' },
  { id: 'voz', label: '5. Voz Algenib', icon: 'record_voice_over' },
  { id: 'movimiento', label: '6. Movimiento', icon: 'videocam' },
  { id: 'referencias', label: '7. Referencias', icon: 'collections' },
  { id: 'resultado', label: '8. Producción & Vídeo', icon: 'smart_display' },
];

export const TopNavigation: React.FC<TopNavigationProps> = ({
  currentTab,
  onSelectTab,
  hasApprovedSheet,
  selectedReferencesCount,
  approvedNewsCount,
  onOpenHelp,
  onOpenBackupModal,
}) => {
  return (
    <header className="border-b border-slate-800 bg-slate-950/90 backdrop-blur sticky top-0 z-30 px-3 md:px-4 py-2.5">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
        {/* Identidad de la estación */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-gradient-to-tr from-amber-600 via-orange-500 to-amber-300 flex items-center justify-center shadow-lg shadow-amber-950/40 text-slate-950 font-black text-sm">
            N•
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-white tracking-wide text-sm">neural.news Studio</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20">
                NeuralStories Broadcast
              </span>
            </div>
            <p className="text-[11px] text-slate-400">@neuraldotai • Sistema Editorial y Producción Audiovisual IA</p>
          </div>
        </div>

        {/* Pestañas de flujo */}
        <nav className="flex items-center gap-1 overflow-x-auto py-1 scrollbar-none order-3 lg:order-2 w-full lg:w-auto">
          {TABS.map((tab) => {
            const isActive = currentTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onSelectTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all whitespace-nowrap cursor-pointer ${
                  isActive
                    ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20 font-semibold'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <span className="material-symbols-outlined text-[16px]">{tab.icon}</span>
                <span>{tab.label}</span>
                {tab.id === 'noticias' && approvedNewsCount > 0 && (
                  <span className="px-1.5 py-0.2 rounded-full bg-slate-900 text-emerald-400 text-[10px] font-mono font-bold border border-emerald-500/40 ml-0.5">
                    {approvedNewsCount}
                  </span>
                )}
                {tab.id === 'personaje' && hasApprovedSheet && (
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block ml-0.5" />
                )}
                {tab.id === 'referencias' && selectedReferencesCount > 0 && (
                  <span className="px-1.5 py-0.2 rounded-full bg-slate-900 text-amber-400 text-[10px] font-mono font-bold border border-amber-500/40 ml-0.5">
                    {selectedReferencesCount}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Acciones principales de la barra superior: Botón Prominente de Descarga */}
        <div className="flex items-center gap-2 order-2 lg:order-3">
          {onOpenBackupModal && (
            <button
              onClick={onOpenBackupModal}
              id="btn-download-full-code"
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-bold rounded-md shadow-md shadow-amber-500/20 transition-all cursor-pointer ring-1 ring-amber-400/50 hover:scale-[1.02] active:scale-[0.98]"
              title="Descargar paquete JSON con los 17 archivos íntegros del proyecto"
            >
              <span className="material-symbols-outlined text-[16px] font-bold">download_for_offline</span>
              <span>Descargar código completo</span>
            </button>
          )}

          <button
            onClick={onOpenHelp}
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs text-slate-400 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-700/60 rounded-md transition-colors cursor-pointer"
            title="Ver especificaciones del sistema editorial y audiovisual"
          >
            <span className="material-symbols-outlined text-[16px]">info</span>
            <span className="hidden sm:inline">Manual y Contrato</span>
          </button>
        </div>
      </div>
    </header>
  );
};