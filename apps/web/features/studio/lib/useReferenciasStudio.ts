'use client';

/**
 * Referencias del Studio: audiovisual (personaje, fondo, escena, estilo) y
 * editorial (enlaces, documentos, transcripciones). Extraído de `App.tsx`
 * (NN-113.13).
 *
 * Regla de negocio: una referencia sólo entra en el prompt si está **aprobada**.
 */
import { useCallback } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { EditorialReferenceItem, VisualReferenceItem } from '../types';

export interface OpcionesReferencias {
  setVisualReferences: Dispatch<SetStateAction<VisualReferenceItem[]>>;
  setEditorialReferences: Dispatch<SetStateAction<EditorialReferenceItem[]>>;
  setSuccessToast: (mensaje: string | null) => void;
}

export interface GestorReferencias {
  handleToggleSelectVisualRef: (id: string) => void;
  handleTogglePermanentVisualRef: (id: string) => void;
  handleAddVisualRef: (item: Omit<VisualReferenceItem, 'id' | 'createdAt' | 'refType'>) => void;
  handleDeleteVisualRef: (id: string) => void;
  handleAddEditorialRef: (item: Omit<EditorialReferenceItem, 'id' | 'createdAt' | 'refType'>) => void;
  handleDeleteEditorialRef: (id: string) => void;
}

export function useReferenciasStudio({
  setVisualReferences,
  setEditorialReferences,
  setSuccessToast,
}: OpcionesReferencias): GestorReferencias {
  const handleToggleSelectVisualRef = useCallback(
    (id: string) => {
      setVisualReferences((prev) =>
        prev.map((r) => {
          if (r.id !== id) return r;
          if (r.status !== 'aprobado') return r;
          return { ...r, selectedForPrompt: !r.selectedForPrompt };
        }),
      );
    },
    [setVisualReferences],
  );

  const handleTogglePermanentVisualRef = useCallback(
    (id: string) => {
      setVisualReferences((prev) =>
        prev.map((r) => {
          if (r.id !== id) return r;
          return { ...r, isEpisodePermanent: !r.isEpisodePermanent };
        }),
      );
    },
    [setVisualReferences],
  );

  const handleAddVisualRef = useCallback(
    (item: Omit<VisualReferenceItem, 'id' | 'createdAt' | 'refType'>) => {
      const newItem: VisualReferenceItem = {
        ...item,
        id: `ref-vis-${Date.now()}`,
        refType: 'audiovisual',
        createdAt: new Date().toISOString().split('T')[0],
      };
      setVisualReferences((prev) => [newItem, ...prev]);
      setSuccessToast(`Referencia [${newItem.identifier}] registrada.`);
      setTimeout(() => setSuccessToast(null), 3000);
    },
    [setVisualReferences, setSuccessToast],
  );

  const handleDeleteVisualRef = useCallback(
    (id: string) => {
      setVisualReferences((prev) => prev.filter((r) => r.id !== id));
    },
    [setVisualReferences],
  );

  const handleAddEditorialRef = useCallback(
    (item: Omit<EditorialReferenceItem, 'id' | 'createdAt' | 'refType'>) => {
      const newItem: EditorialReferenceItem = {
        ...item,
        id: `ed-ref-${Date.now()}`,
        refType: 'editorial',
        createdAt: new Date().toISOString().split('T')[0],
      };
      setEditorialReferences((prev) => [newItem, ...prev]);
      setSuccessToast(`Referencia editorial [${newItem.identifier}] añadida.`);
      setTimeout(() => setSuccessToast(null), 3000);
    },
    [setEditorialReferences, setSuccessToast],
  );

  const handleDeleteEditorialRef = useCallback(
    (id: string) => {
      setEditorialReferences((prev) => prev.filter((e) => e.id !== id));
    },
    [setEditorialReferences],
  );

  return {
    handleToggleSelectVisualRef,
    handleTogglePermanentVisualRef,
    handleAddVisualRef,
    handleDeleteVisualRef,
    handleAddEditorialRef,
    handleDeleteEditorialRef,
  };
}
