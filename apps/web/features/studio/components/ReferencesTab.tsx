import React, { useState, useRef } from 'react';
import { Flow } from '../flow/adapter';
import { 
  VisualReferenceItem, 
  EditorialReferenceItem, 
  VisualReferenceCategory, 
  EditorialSourceType, 
  ApprovalStatus 
} from '../types';

interface ReferencesTabProps {
  visualReferences: VisualReferenceItem[];
  editorialReferences: EditorialReferenceItem[];
  onToggleSelectVisualRef: (id: string) => void;
  onUpdateVisualRefStatus: (id: string, status: ApprovalStatus) => void;
  onTogglePermanentVisualRef: (id: string) => void;
  onAddVisualRef: (item: Omit<VisualReferenceItem, 'id' | 'createdAt' | 'refType'>) => void;
  onDeleteVisualRef: (id: string) => void;
  onAddEditorialRef: (item: Omit<EditorialReferenceItem, 'id' | 'createdAt' | 'refType'>) => void;
  onDeleteEditorialRef: (id: string) => void;
  onExportConfiguration: () => Promise<void>;
  onImportConfigurationJson: (imported: any) => void;
  isExporting: boolean;
}

export const ReferencesTab: React.FC<ReferencesTabProps> = ({
  visualReferences,
  editorialReferences,
  onToggleSelectVisualRef,
  onUpdateVisualRefStatus,
  onTogglePermanentVisualRef,
  onAddVisualRef,
  onDeleteVisualRef,
  onAddEditorialRef,
  onDeleteEditorialRef,
  onExportConfiguration,
  onImportConfigurationJson,
  isExporting,
}) => {
  const [activeTypeTab, setActiveTypeTab] = useState<'audiovisual' | 'editorial'>('audiovisual');
  const [visualCategory, setVisualCategory] = useState<VisualReferenceCategory | 'todos'>('todos');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterApprovedOnly, setFilterApprovedOnly] = useState(false);

  // Formulario de referencia audiovisual
  const [showAddVisualModal, setShowAddVisualModal] = useState(false);
  const [vName, setVName] = useState('');
  const [vIdentifier, setVIdentifier] = useState('');
  const [vCategory, setVCategory] = useState<VisualReferenceCategory>('personaje');
  const [vImageUrl, setVImageUrl] = useState('');
  const [vMediaId, setVMediaId] = useState<string | undefined>(undefined);
  const [vDescription, setVDescription] = useState('');
  const [vVersion, setVVersion] = useState('v1.0');
  const [vStatus, setVStatus] = useState<ApprovalStatus>('aprobado');
  const [vIsPermanent, setVIsPermanent] = useState(false);
  const [vTags, setVTags] = useState('');

  // Formulario de referencia editorial
  const [showAddEditorialModal, setShowAddEditorialModal] = useState(false);
  const [eTitle, setETitle] = useState('');
  const [eIdentifier, setEIdentifier] = useState('');
  const [eSourceType, setESourceType] = useState<EditorialSourceType>('enlace');
  const [eUrl, setEUrl] = useState('');
  const [eExcerpt, setEExcerpt] = useState('');
  const [eAuthor, setEAuthor] = useState('');

  const configFileInputRef = useRef<HTMLInputElement>(null);
  const imageFileInputRef = useRef<HTMLInputElement>(null);

  // Selección directa desde Flow Media Gallery para comprobar transferibilidad real
  const handleSelectFromFlowGallery = async () => {
    try {
      const media = await Flow.media.select({ filter: 'image' });
      setVMediaId(media.mediaId);
      setVImageUrl(`data:${media.mimeType};base64,${media.base64}`);
      if (!vName) setVName(media.name ? media.name.replace(/\.[^/.]+$/, '') : 'Referencia de Galería');
      if (!vIdentifier) setVIdentifier(`REF-${vCategory.toUpperCase().slice(0, 4)}-${Math.floor(100 + Math.random() * 900)}`);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSaveVisual = () => {
    if (!vName.trim() || !vIdentifier.trim() || !vImageUrl.trim()) return;
    onAddVisualRef({
      name: vName.trim(),
      identifier: vIdentifier.trim().toUpperCase(),
      category: vCategory,
      imageUrl: vImageUrl.trim(),
      mediaId: vMediaId,
      description: vDescription.trim() || 'Sin descripción adicional.',
      version: vVersion.trim() || 'v1.0',
      status: vStatus,
      selectedForPrompt: vStatus === 'aprobado',
      isEpisodePermanent: vIsPermanent,
      tags: vTags.split(',').map(t => t.trim().toLowerCase()).filter(t => t.length > 0)
    });
    // Reset
    setVName('');
    setVIdentifier('');
    setVImageUrl('');
    setVMediaId(undefined);
    setVDescription('');
    setShowAddVisualModal(false);
  };

  const handleSaveEditorial = () => {
    if (!eTitle.trim() || !eIdentifier.trim()) return;
    onAddEditorialRef({
      identifier: eIdentifier.trim().toUpperCase(),
      title: eTitle.trim(),
      sourceType: eSourceType,
      urlOrCitation: eUrl.trim(),
      summaryOrExcerpt: eExcerpt.trim(),
      authorOrChannel: eAuthor.trim() || undefined,
      status: 'aprobado'
    });
    setETitle('');
    setEIdentifier('');
    setEUrl('');
    setEExcerpt('');
    setShowAddEditorialModal(false);
  };

  return (
    <div className="space-y-6">
      {/* Cabecera y Selección de Tipo de Biblioteca */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-white">
                Biblioteca Dual de Referencias: Audiovisuales vs Editoriales
              </h3>
            </div>
            <p className="text-xs text-neutral-400 mt-1 max-w-3xl leading-relaxed">
              Distingue rigurosamente entre <strong>referencias editoriales</strong> (documentos, transcripciones de YouTube/Spotify, citas) 
              y <strong>referencias audiovisuales</strong> (hojas del presentador @neuraldotai, plató CRT, estilos de 8s). 
              Las referencias aprobadas del personaje y fondo pueden fijarse permanentemente en todos los episodios.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 self-start lg:self-auto">
            {activeTypeTab === 'audiovisual' ? (
              <button
                onClick={() => setShowAddVisualModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-sky-500 hover:bg-sky-400 text-neutral-950 font-bold rounded text-xs transition cursor-pointer shadow-md shadow-sky-500/20"
              >
                <span>Nueva Ref. Audiovisual</span>
              </button>
            ) : (
              <button
                onClick={() => setShowAddEditorialModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-sky-500 hover:bg-sky-400 text-neutral-950 font-bold rounded text-xs transition cursor-pointer shadow-md shadow-sky-500/20"
              >
                <span>Nueva Ref. Editorial</span>
              </button>
            )}

            <button
              onClick={() => configFileInputRef.current?.click()}
              className="flex items-center gap-1.5 px-2.5 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 border border-neutral-700 rounded text-xs font-medium transition cursor-pointer"
            >
              <span className="hidden sm:inline">Importar</span>
            </button>
            <input
              type="file"
              ref={configFileInputRef}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                const r = new FileReader();
                r.onload = () => onImportConfigurationJson(JSON.parse(r.result as string));
                r.readAsText(file);
                e.target.value = '';
              }}
              accept=".json"
              className="hidden"
            />

            <button
              onClick={onExportConfiguration}
              disabled={isExporting}
              className="flex items-center gap-1.5 px-2.5 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 border border-neutral-700 rounded text-xs font-medium transition cursor-pointer disabled:opacity-50"
            >
              <span className="hidden sm:inline">Exportar</span>
            </button>
          </div>
        </div>

        {/* Selector de Tipo (Audiovisual vs Editorial) */}
        <div className="mt-4 pt-3 border-t border-neutral-800/80 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTypeTab('audiovisual')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-bold transition cursor-pointer ${
                activeTypeTab === 'audiovisual'
                  ? 'bg-sky-500 text-neutral-950 shadow'
                  : 'bg-neutral-950 text-neutral-400 hover:text-white border border-neutral-800'
              }`}
            >
              <span>Referencias Audiovisuales ({visualReferences.length})</span>
            </button>
            <button
              onClick={() => setActiveTypeTab('editorial')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-bold transition cursor-pointer ${
                activeTypeTab === 'editorial'
                  ? 'bg-sky-500 text-neutral-950 shadow'
                  : 'bg-neutral-950 text-neutral-400 hover:text-white border border-neutral-800'
              }`}
            >
              <span>Referencias Editoriales ({editorialReferences.length})</span>
            </button>
          </div>

          <label className="flex items-center gap-1.5 text-neutral-400 cursor-pointer text-xs select-none">
            <input
              type="checkbox"
              checked={filterApprovedOnly}
              onChange={(e) => setFilterApprovedOnly(e.target.checked)}
              className="accent-sky-500 rounded cursor-pointer"
            />
            <span>Solo aprobadas</span>
          </label>
        </div>
      </div>

      {/* SECCIÓN AUDIOVISUAL */}
      {activeTypeTab === 'audiovisual' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {visualReferences.map((ref) => {
              const isSelected = ref.selectedForPrompt && ref.status === 'aprobado';
              const hasFlowMediaId = Boolean(ref.mediaId);

              return (
                <div
                  key={ref.id}
                  className={`bg-neutral-900 rounded-lg border transition-all flex flex-col justify-between overflow-hidden ${
                    isSelected
                      ? 'border-sky-500 ring-1 ring-sky-500/50 shadow-lg shadow-sky-950/30'
                      : 'border-neutral-800 hover:border-neutral-700'
                  }`}
                >
                  <div className="relative aspect-video bg-neutral-950 overflow-hidden flex items-center justify-center border-b border-neutral-800/80">
                    <img src={ref.imageUrl} alt={ref.name} className="w-full h-full object-cover" />
                    <span className="absolute top-2 left-2 px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-neutral-950/85 backdrop-blur text-neutral-300 border border-neutral-700/80">
                      {ref.category}
                    </span>
                    {ref.isEpisodePermanent && (
                      <span className="absolute top-2 right-2 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-500 text-neutral-950 shadow">
                        PERMANENTE ⚓
                      </span>
                    )}
                    <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-neutral-950/90 backdrop-blur text-[10px] font-mono text-white font-bold border border-neutral-800">
                      {ref.identifier}
                    </div>
                  </div>

                  <div className="p-3.5 space-y-2 flex-1 flex flex-col justify-between">
                    <div>
                      <h5 className="text-xs font-bold text-white line-clamp-1">{ref.name}</h5>
                      <p className="text-[11px] text-neutral-400 mt-1 line-clamp-2 leading-relaxed">{ref.description}</p>
                    </div>

                    {/* Verificación de transferencia real a Flow */}
                    <div className="p-1.5 rounded bg-neutral-950 border border-neutral-800 text-[10px] font-mono flex items-center justify-between">
                      <span className="text-neutral-500">Transferible a Flow:</span>
                      <span className={hasFlowMediaId ? 'text-emerald-400 font-bold' : 'text-sky-400'}>
                        {hasFlowMediaId ? '✓ mediaId activo' : 'Directriz Prompt'}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs pt-1">
                      <button
                        onClick={() => onTogglePermanentVisualRef(ref.id)}
                        className={`text-[10px] font-mono cursor-pointer ${
                          ref.isEpisodePermanent ? 'text-sky-400 font-bold' : 'text-neutral-500 hover:text-neutral-300'
                        }`}
                      >
                        {ref.isEpisodePermanent ? '⚓ Fijado en Episodio' : 'Fijar en Episodio'}
                      </button>
                      <button
                        onClick={() => onDeleteVisualRef(ref.id)}
                        className="text-neutral-500 hover:text-rose-400 cursor-pointer"
                      >
                        </button>
                    </div>
                  </div>

                  <div className="p-2.5 bg-neutral-950 border-t border-neutral-800 flex items-center justify-between gap-2">
                    <button
                      onClick={() => onToggleSelectVisualRef(ref.id)}
                      className={`flex-1 py-1 px-2 rounded text-xs font-semibold cursor-pointer ${
                        isSelected ? 'bg-sky-500 text-neutral-950 font-bold' : 'bg-neutral-800 text-neutral-300'
                      }`}
                    >
                      {isSelected ? 'En Prompt ✓' : 'Usar en Prompt'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* SECCIÓN EDITORIAL */}
      {activeTypeTab === 'editorial' && (
        <div className="space-y-3">
          {editorialReferences.map((ed) => (
            <div
              key={ed.id}
              className="bg-neutral-900 rounded-lg border border-neutral-800 p-4 flex flex-col md:flex-row items-start justify-between gap-4"
            >
              <div className="space-y-1.5 flex-1">
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-neutral-950 text-cyan-400 border border-neutral-800">
                    {ed.identifier}
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-neutral-950 text-neutral-400">
                    {ed.sourceType}
                  </span>
                  {ed.authorOrChannel && (
                    <span className="text-[11px] text-neutral-400 font-medium">
                      Fuente: {ed.authorOrChannel}
                    </span>
                  )}
                </div>

                <h4 className="text-xs font-bold text-white">{ed.title}</h4>
                <p className="text-xs text-neutral-300 leading-relaxed font-mono bg-neutral-950 p-2 rounded border border-neutral-800/60">
                  "{ed.summaryOrExcerpt}"
                </p>

                {ed.urlOrCitation && (
                  <a
                    href={ed.urlOrCitation}
                    target="_self"
                    className="text-[11px] text-sky-400/90 font-mono hover:underline truncate block"
                  >
                    {ed.urlOrCitation}
                  </a>
                )}
              </div>

              <button
                onClick={() => onDeleteEditorialRef(ed.id)}
                className="text-neutral-500 hover:text-rose-400 p-1 cursor-pointer"
              >
                </button>
            </div>
          ))}
        </div>
      )}

      {/* Modal Nueva Referencia Audiovisual */}
      {showAddVisualModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl max-w-xl w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-sm font-bold text-white">Añadir Referencia Audiovisual Canónica</h3>
            <div className="space-y-3 text-xs">
              <input
                type="text"
                placeholder="Nombre (ej: NeuralDotAI - Perfil 3/4)"
                value={vName}
                onChange={(e) => setVName(e.target.value)}
                className="w-full bg-neutral-950 border border-neutral-800 rounded p-2 text-neutral-200"
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="text"
                  placeholder="ID (REF-CHAR-02)"
                  value={vIdentifier}
                  onChange={(e) => setVIdentifier(e.target.value)}
                  className="bg-neutral-950 border border-neutral-800 rounded p-2 text-neutral-200 font-mono"
                />
                <select
                  value={vCategory}
                  onChange={(e) => setVCategory(e.target.value as VisualReferenceCategory)}
                  className="bg-neutral-950 border border-neutral-800 rounded p-2 text-neutral-200"
                >
                  <option value="personaje">Personaje</option>
                  <option value="fondo">Fondo CRT</option>
                  <option value="escena">Escena</option>
                  <option value="estilo">Estilo</option>
                </select>
              </div>

              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="URL o selecciona de Flow Media Gallery"
                  value={vImageUrl}
                  onChange={(e) => setVImageUrl(e.target.value)}
                  className="flex-1 bg-neutral-950 border border-neutral-800 rounded p-2 text-neutral-200 text-xs font-mono"
                />
                <button
                  type="button"
                  onClick={handleSelectFromFlowGallery}
                  className="px-3 py-1 bg-neutral-800 hover:bg-neutral-700 text-sky-400 rounded text-xs font-semibold cursor-pointer border border-neutral-700"
                >
                  Galería Flow
                </button>
              </div>

              <textarea
                placeholder="Directriz de consistencia visual..."
                value={vDescription}
                onChange={(e) => setVDescription(e.target.value)}
                rows={2}
                className="w-full bg-neutral-950 border border-neutral-800 rounded p-2 text-neutral-200"
              />

              <label className="flex items-center gap-2 text-neutral-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={vIsPermanent}
                  onChange={(e) => setVIsPermanent(e.target.checked)}
                  className="accent-sky-500 rounded"
                />
                <span>Fijar como elemento permanente del plató/personaje</span>
              </label>
            </div>

            <div className="pt-2 border-t border-neutral-800 flex justify-end gap-2">
              <button
                onClick={() => setShowAddVisualModal(false)}
                className="px-3 py-1.5 bg-neutral-800 text-neutral-300 rounded text-xs cursor-pointer"
              >
                Cancelar
              </button>
              <button
                onClick={handleSaveVisual}
                className="px-4 py-1.5 bg-sky-500 text-neutral-950 font-bold rounded text-xs cursor-pointer"
              >
                Guardar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Nueva Referencia Editorial */}
      {showAddEditorialModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl max-w-xl w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-sm font-bold text-white">Añadir Referencia Editorial (Documental)</h3>
            <div className="space-y-3 text-xs">
              <input
                type="text"
                placeholder="Título del documento o transcripción"
                value={eTitle}
                onChange={(e) => setETitle(e.target.value)}
                className="w-full bg-neutral-950 border border-neutral-800 rounded p-2 text-neutral-200"
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="text"
                  placeholder="ID (ED-SRC-04)"
                  value={eIdentifier}
                  onChange={(e) => setEIdentifier(e.target.value)}
                  className="bg-neutral-950 border border-neutral-800 rounded p-2 text-neutral-200 font-mono"
                />
                <select
                  value={eSourceType}
                  onChange={(e) => setESourceType(e.target.value as EditorialSourceType)}
                  className="bg-neutral-950 border border-neutral-800 rounded p-2 text-neutral-200"
                >
                  <option value="enlace">Enlace Web</option>
                  <option value="documento">Documento Técnico / Paper</option>
                  <option value="transcripcion_youtube">Transcripción YouTube</option>
                  <option value="transcripcion_spotify">Transcripción Spotify</option>
                  <option value="comunicado_oficial">Comunicado Oficial</option>
                </select>
              </div>

              <input
                type="text"
                placeholder="URL o Cita bibliográfica"
                value={eUrl}
                onChange={(e) => setEUrl(e.target.value)}
                className="w-full bg-neutral-950 border border-neutral-800 rounded p-2 text-neutral-200 font-mono"
              />

              <textarea
                placeholder="Extracto clave o síntesis textual comprobada..."
                value={eExcerpt}
                onChange={(e) => setEExcerpt(e.target.value)}
                rows={3}
                className="w-full bg-neutral-950 border border-neutral-800 rounded p-2 text-neutral-200 font-mono"
              />
            </div>

            <div className="pt-2 border-t border-neutral-800 flex justify-end gap-2">
              <button
                onClick={() => setShowAddEditorialModal(false)}
                className="px-3 py-1.5 bg-neutral-800 text-neutral-300 rounded text-xs cursor-pointer"
              >
                Cancelar
              </button>
              <button
                onClick={handleSaveEditorial}
                className="px-4 py-1.5 bg-sky-500 text-neutral-950 font-bold rounded text-xs cursor-pointer"
              >
                Guardar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};