import React from 'react';
import { StudioTab } from '../types';

interface TopNavigationProps {
  currentTab: StudioTab;
  onSelectTab: (tab: StudioTab) => void;
  hasApprovedSheet: boolean;
  selectedReferencesCount: number;
  approvedNewsCount: number;
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
        <span className="px-1.5 py-0.2 rounded-full bg-neutral-900 text-emerald-400 text-[10px] font-mono font-bold border border-emerald-500/40 ml-0.5">
          {approvedNewsCount}
        </span>
      );
    }
    if (tab.id === 'referencias' && selectedReferencesCount > 0) {
      return (
        <span className="px-1.5 py-0.2 rounded-full bg-neutral-900 text-sky-400 text-[10px] font-mono font-bold border border-sky-500/40 ml-0.5">
          {selectedReferencesCount}
        </span>
      );
    }
    return null;
  };

  return (
    <header
      className={`border-b border-neutral-800 bg-neutral-950/90 backdrop-blur sticky top-0 z-30 px-3 md:px-4 ${
        embedded ? 'py-1.5' : 'py-2.5'
      }`}
    >
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
        {/* La identidad la aporta el shell de neural.news: sin cabecera duplicada */}

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
                {index > 0 && <div aria-hidden className="h-7 w-px bg-neutral-700/70" />}
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-neutral-500">
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
                              ? 'bg-sky-500 text-neutral-950 shadow-md shadow-sky-500/20 font-semibold'
                              : 'text-neutral-300 hover:text-white hover:bg-neutral-800/60'
                          }`}
                        >
                          <span>{tab.label}</span>
                          <span
                            aria-hidden
                            className={`text-[11px] ${
                              isActive
                                ? 'text-neutral-900'
                                : state === 'done'
                                  ? 'text-emerald-400'
                                  : state === 'attention'
                                    ? 'text-sky-400'
                                    : 'text-neutral-600'
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
              <span className="block text-[10px] uppercase tracking-wide text-neutral-500">
                {current ? PHASES.find((p) => p.id === current.phase)?.label : 'Estudio'}
              </span>
              <span className="block text-sm font-semibold text-neutral-100 truncate">
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
              className="min-h-9 rounded-md border border-neutral-700 bg-neutral-900 px-2 py-1 text-xs text-neutral-200"
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

      </div>
    </header>
  );
};
