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
  /** Modo integrado dentro de neural.news: la identidad la pone el shell externo. */
  embedded?: boolean;
}

/**
 * Navegación por proceso, no por pestañas sueltas.
 *
 * Las ocho secciones siguen existiendo (no se pierde ninguna función); lo que
 * cambia es su representación: agrupadas en las cuatro fases del flujo
 * (Entrada → Identidad → Planificación → Salida) y con un estado visible
 * (completo / requiere atención / pendiente).
 */
type Phase = 'entrada' | 'identidad' | 'planificacion' | 'salida';

interface TabDef {
  id: StudioTab;
  label: string;
  shortLabel: string;
  icon: string;
  phase: Phase;
}

const TABS: TabDef[] = [
  { id: 'noticias', label: 'Noticias', shortLabel: 'Noticias', icon: 'newspaper', phase: 'entrada' },
  { id: 'personaje', label: 'Personaje', shortLabel: 'Personaje', icon: 'badge', phase: 'identidad' },
  { id: 'fondo', label: 'Fondo CRT', shortLabel: 'Fondo', icon: 'tv', phase: 'identidad' },
  { id: 'voz', label: 'Voz Algenib', shortLabel: 'Voz', icon: 'record_voice_over', phase: 'identidad' },
  { id: 'guion', label: 'Guion y Escenas', shortLabel: 'Guion', icon: 'article', phase: 'planificacion' },
  { id: 'movimiento', label: 'Movimiento', shortLabel: 'Movimiento', icon: 'videocam', phase: 'planificacion' },
  { id: 'referencias', label: 'Referencias', shortLabel: 'Referencias', icon: 'collections', phase: 'planificacion' },
  { id: 'resultado', label: 'Producción y Vídeo', shortLabel: 'Producción', icon: 'smart_display', phase: 'salida' },
];

const PHASES: { id: Phase; label: string }[] = [
  { id: 'entrada', label: 'Entrada' },
  { id: 'identidad', label: 'Identidad' },
  { id: 'planificacion', label: 'Planificación' },
  { id: 'salida', label: 'Salida' },
];

export const TopNavigation: React.FC<TopNavigationProps> = ({
  currentTab,
  onSelectTab,
  hasApprovedSheet,
  selectedReferencesCount,
  approvedNewsCount,
  onOpenHelp,
  onOpenBackupModal,
  embedded = false,
}) => {
  const current = TABS.find((t) => t.id === currentTab);

  /** Estado de cada sección: hecho (✓), requiere atención (!) o pendiente (○). */
  const stateOf = (tab: TabDef): 'done' | 'attention' | 'pending' => {
    if (tab.id === 'noticias') {
      if (approvedNewsCount === 0) return 'attention';
      return 'done';
    }
    if (tab.id === 'personaje') return hasApprovedSheet ? 'done' : 'pending';
    if (tab.id === 'referencias') return selectedReferencesCount > 0 ? 'done' : 'pending';
    if (tab.id === 'resultado') return 'pending';
    return 'pending';
  };

  const badge = (tab: TabDef) => {
    if (tab.id === 'noticias' && approvedNewsCount > 0) {
      return (
        <span className="px-1.5 py-0.2 rounded-full bg-slate-900 text-emerald-400 text-[10px] font-mono font-bold border border-emerald-500/40 ml-0.5">
          {approvedNewsCount}
        </span>
      );
    }
    if (tab.id === 'referencias' && selectedReferencesCount > 0) {
      return (
        <span className="px-1.5 py-0.2 rounded-full bg-slate-900 text-amber-400 text-[10px] font-mono font-bold border border-amber-500/40 ml-0.5">
          {selectedReferencesCount}
        </span>
      );
    }
    return null;
  };

  return (
    <header
      className={`border-b border-slate-800 bg-slate-950/90 backdrop-blur sticky top-0 z-30 px-3 md:px-4 ${
        embedded ? 'py-1.5' : 'py-2.5'
      }`}
    >
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
        {/* Identidad de la estación (oculta en modo integrado: la pone el shell de neural.news) */}
        {!embedded && (
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
        )}

        {/* Navegación por proceso: en pantallas estrechas, «paso actual + menú» */}
        <nav
          aria-label="Secciones del estudio"
          className={`flex items-center gap-2 overflow-x-auto py-1 scrollbar-none ${
            embedded ? 'w-full order-1' : 'order-3 lg:order-2 w-full lg:w-auto'
          }`}
        >
          {/* Los grupos bajan de línea si no caben: nunca se recortan. */}
          <div className="hidden lg:flex lg:flex-wrap items-center gap-x-3 gap-y-1">
            {PHASES.map((phase, index) => (
              <div key={phase.id} className="flex items-center gap-2">
                {index > 0 && <div aria-hidden className="h-7 w-px bg-slate-700/70" />}
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                    {phase.label}
                  </span>
                  <div className="flex items-center gap-1">
                    {TABS.filter((tab) => tab.phase === phase.id).map((tab) => {
                      const isActive = currentTab === tab.id;
                      const state = stateOf(tab);
                      return (
                        <button
                          key={tab.id}
                          onClick={() => onSelectTab(tab.id)}
                          aria-current={isActive ? 'page' : undefined}
                          title={`${tab.label} — ${state === 'done' ? 'completo' : state === 'attention' ? 'requiere atención' : 'pendiente'}`}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all whitespace-nowrap cursor-pointer ${
                            isActive
                              ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20 font-semibold'
                              : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                          }`}
                        >
                          <span className="material-symbols-outlined text-[16px]">{tab.icon}</span>
                          <span>{tab.label}</span>
                          <span
                            aria-hidden
                            className={`text-[11px] ${
                              isActive
                                ? 'text-slate-900'
                                : state === 'done'
                                  ? 'text-emerald-400'
                                  : state === 'attention'
                                    ? 'text-amber-400'
                                    : 'text-slate-600'
                            }`}
                          >
                            {state === 'done' ? '✓' : state === 'attention' ? '!' : '○'}
                          </span>
                          {badge(tab)}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Móvil: paso actual + menú de secciones */}
          <div className="flex lg:hidden w-full items-center gap-2">
            <div className="min-w-0 flex-1">
              <span className="block text-[10px] uppercase tracking-wide text-slate-500">
                {current ? PHASES.find((p) => p.id === current.phase)?.label : 'Estudio'}
              </span>
              <span className="block text-sm font-semibold text-slate-100 truncate">
                {current?.label ?? 'Estudio'}
              </span>
            </div>
            <label className="sr-only" htmlFor="studio-section">
              Cambiar de sección
            </label>
            <select
              id="studio-section"
              value={currentTab}
              onChange={(e) => onSelectTab(e.target.value as StudioTab)}
              className="min-h-9 rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200"
            >
              {PHASES.map((phase) => (
                <optgroup key={phase.id} label={phase.label}>
                  {TABS.filter((tab) => tab.phase === phase.id).map((tab) => (
                    <option key={tab.id} value={tab.id}>
                      {tab.label}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
        </nav>

        {/* Acciones principales de la barra superior */}
        {!embedded && (
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
        )}
      </div>
    </header>
  );
};
