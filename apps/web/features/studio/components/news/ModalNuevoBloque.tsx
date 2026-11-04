import React, { useState } from 'react';
import { IconoCruce } from '@/components/ui/icono';

/**
 * Modal de creación de un bloque o episodio de la escaleta (NN-113.13).
 *
 * Antes vivía dentro de `NewsEditorialTab.tsx` (759 líneas).
 */
interface ModalNuevoBloqueProps {
  onCrear: (titulo: string, notas?: string) => void;
  onCerrar: () => void;
}

export const ModalNuevoBloque: React.FC<ModalNuevoBloqueProps> = ({ onCrear, onCerrar }) => {
  const [newBlockTitle, setNewBlockTitle] = useState('');
  const [newBlockNotes, setNewBlockNotes] = useState('');

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-neutral-900 border border-neutral-800 rounded-md max-w-md w-full p-6 space-y-4 shadow-2xl">
        <div className="panel-header">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-ink">Nuevo Bloque / Episodio</h3>
          </div>
          <button
            onClick={onCerrar}
            aria-label="Cerrar la ventana de nuevo bloque"
            title="Cerrar"
            className="text-neutral-400 hover:text-ink p-1 rounded cursor-pointer"
          >
            <IconoCruce />
          </button>
        </div>

        <div className="space-y-3 text-xs">
          <div>
            <label className="block text-neutral-400 font-medium mb-1">Nombre del Bloque *</label>
            <input aria-label="Nombre del Bloque *"
              type="text"
              value={newBlockTitle}
              onChange={(e) => setNewBlockTitle(e.target.value)}
              placeholder="Ej: Episodio 43 - Especial Semiconductores"
              className="input-compact"
            />
          </div>

          <div>
            <label className="block text-neutral-400 font-medium mb-1">Notas de Producción</label>
            <textarea aria-label="Notas de Producción"
              value={newBlockNotes}
              onChange={(e) => setNewBlockNotes(e.target.value)}
              rows={2}
              placeholder="Notas de escaleta..."
              className="input-compact"
            />
          </div>
        </div>

        <div className="modal-actions">
          <button
            type="button"
            onClick={onCerrar}
            className="px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded text-xs transition cursor-pointer"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={() => {
              if (newBlockTitle.trim()) {
                onCrear(newBlockTitle.trim(), newBlockNotes.trim());
                setNewBlockTitle('');
                setNewBlockNotes('');
                onCerrar();
              }
            }}
            className="px-4 py-1.5 bg-sky-500 hover:bg-sky-400 text-neutral-950 font-bold rounded text-xs transition cursor-pointer"
          >
            Crear Bloque
          </button>
        </div>
      </div>
    </div>
  );
};
