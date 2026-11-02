export type StudioTab = 
  | 'noticias'
  | 'personaje' 
  | 'fondo' 
  | 'guion' 
  | 'voz' 
  | 'movimiento' 
  | 'referencias' 
  | 'resultado';

export interface CharacterPreset {
  name: string;
  handle: string;
  show: string;
  features: {
    face: string;
    glasses: string;
    hair: string;
    beard: string;
    age: string;
    wardrobe: string;
  };
}

export interface MasterSheetState {
  mediaId?: string;
  base64?: string;
  mimeType?: string;
  isApproved: boolean;
  notes: string;
}

export interface BackgroundPreset {
  id: string;
  title: string;
  description: string;
  aspectRatio: '16:9' | '9:16';
  promptDescriptor: string;
}

export interface VoiceConfig {
  profile: string;
  gender: string;
  timbre: string;
  locale: string;
  speedMultiplier: number;
  cadenceDescription: string;
}

export interface CameraMovement {
  id: string;
  label: string;
  category: 'encuadre' | 'dinamismo' | 'efecto';
  description: string;
  promptInstruction: string;
  selected: boolean;
}

// -------------------------------------------------------------
// SISTEMA DE GUION COMPLETO Y DIVISION EN ESCENAS DE ~8s
// -------------------------------------------------------------
export interface SceneProductionPlan {
  sceneIndex: number;
  scriptSnippet: string;
  wordCount: number;
  estDurationSeconds: number;
  recommendedFraming: string;
  movementInstruction: string;
  transitionType: 'corte_directo' | 'rgb_glitch_flash' | 'whip_pan' | 'push_zoom';
  visualReferenceIds: string[];
  compiledPrompt: string;
}

export interface MultiSceneScriptAnalysis {
  fullWordCount: number;
  fullEstDurationSeconds: number;
  targetDurationSeconds: number;
  scenesCount: number;
  scenes: SceneProductionPlan[];
  paceRating: 'muy_rapido' | 'optimo' | 'lento' | 'excesivo';
  feedback: string;
}

// Compatibilidad con tomas individuales de 8 segundos
export interface NewsScriptAnalysis {
  wordCount: number;
  estDurationSeconds: number;
  isValid8s: boolean;
  paceRating: 'muy_rapido' | 'optimo' | 'lento' | 'excesivo';
  feedback: string;
}

// -------------------------------------------------------------
// SISTEMA DE REFERENCIAS: SEPARACIÓN EDITORIAL vs AUDIOVISUAL
// -------------------------------------------------------------
export type ReferenceType = 'editorial' | 'audiovisual';
export type VisualReferenceCategory = 'personaje' | 'fondo' | 'escena' | 'estilo';
export type EditorialSourceType = 'enlace' | 'documento' | 'transcripcion_youtube' | 'transcripcion_spotify' | 'comunicado_oficial';
export type ApprovalStatus = 'aprobado' | 'pendiente' | 'descartado';

export interface VisualReferenceItem {
  id: string;
  refType: 'audiovisual';
  name: string;
  identifier: string; // e.g., 'REF-CHAR-01'
  category: VisualReferenceCategory;
  imageUrl: string; // URL web o data URL base64
  mediaId?: string; // Opcional si procede de Flow Media Gallery
  description: string;
  version: string;
  status: ApprovalStatus;
  selectedForPrompt: boolean;
  isEpisodePermanent?: boolean; // Fijar como elemento permanente del plató/personaje
  tags?: string[];
  createdAt: string;
}

export interface EditorialReferenceItem {
  id: string;
  refType: 'editorial';
  identifier: string; // e.g., 'ED-SRC-01'
  title: string;
  sourceType: EditorialSourceType;
  urlOrCitation: string;
  summaryOrExcerpt: string;
  authorOrChannel?: string;
  status: ApprovalStatus;
  createdAt: string;
}

export type UnifiedReferenceItem = VisualReferenceItem | EditorialReferenceItem;

// -------------------------------------------------------------
// SISTEMA EDITORIAL DE NOTICIAS (neural.news)
// -------------------------------------------------------------
export type VerificationStatus = 'verificado' | 'en_revision' | 'sin_verificar' | 'descartado';
export type ArticleApprovalStatus = 'aprobada' | 'pendiente' | 'descartada';

export interface NewsArticle {
  id: string;
  uuid?: string;
  slug?: string;
  title: string;
  summary: string;
  fullScript: string;
  date: string;
  verificationStatus: VerificationStatus;
  approvalStatus: ArticleApprovalStatus;
  episodeBlock?: string; // Nombre o ID de bloque/episodio (ej: "Bloque 1: Apertura IA", "Episodio 42")
  orderIndex: number;
  sources: string[];
  editorialReferenceIds: string[];
  visualReferenceIds: string[];
  tags: string[];
  metadata?: {
    importedFrom?: 'manual' | 'batch_json' | 'youtube_transcription' | 'spotify_feed' | 'api_sync';
    externalId?: string;
    verifiedBy?: string;
  };
}

export interface ProductionEpisodeBlock {
  id: string;
  title: string;
  date: string;
  articleIds: string[];
  permanentVisualRefIds: string[];
  notes?: string;
}

// -------------------------------------------------------------
// CONTRATO DE INTEGRACIÓN Y PERSISTENCIA (neural.news v2.0)
// -------------------------------------------------------------
export interface StudioExportPackage {
  formatVersion: '2.0';
  exportedAt: string;
  studio: string;
  contract: 'neural.news-studio-v2';
  articles: NewsArticle[];
  episodeBlocks: ProductionEpisodeBlock[];
  visualReferences: VisualReferenceItem[];
  editorialReferences: EditorialReferenceItem[];
  studioConfig: {
    aspectRatio: '16:9' | '9:16';
    selectedBackgroundId: string;
    voiceSpeedMultiplier: number;
    selectedMovementIds: string[];
    permanentCharacterMediaId?: string;
    permanentBackgroundMediaId?: string;
  };
}

/**
 * Configuración **importada**: un paquete de exportación del que sólo se usan
 * algunas partes. Antes era `any`, lo que impedía que TypeScript detectara un
 * cambio en el contrato de importación (NN-113.3).
 */
export type ConfiguracionImportada = Partial<Omit<StudioExportPackage, 'studioConfig'>> & {
  studioConfig?: Partial<StudioExportPackage['studioConfig']>;
};