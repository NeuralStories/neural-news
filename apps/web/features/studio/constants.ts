import type { 
  CharacterPreset, 
  BackgroundPreset, 
  VoiceConfig, 
  CameraMovement, 
  VisualReferenceItem, 
  EditorialReferenceItem, 
  NewsArticle, 
  ProductionEpisodeBlock 
} from './types';

export const MAXDOTAI_CANONICAL: CharacterPreset = {
  name: 'maxDotAi',
  handle: '@maxDotAi (pendiente de confirmar en cuenta)',
  show: 'NeuralStories News',
  features: {
    face: 'Rostro masculino mediterráneo/ibérico sereno, facciones definidas pero amables',
    glasses: 'Gafas de pasta de diseño contemporáneo, montura rectangular oscura y sobria',
    hair: 'Pelo castaño oscuro corto, peinado ordenado con textura mate',
    beard: 'Barba recortada de 3-4 días, perfilada y cuidada',
    age: 'Aparente 32-35 años, aspecto profesional y tecnológico',
    wardrobe: 'Camisa azul noche oxford o camiseta técnica sobria con blazer oscuro de corte limpio sin adornos estrambóticos'
  }
};

export const DEFAULT_MASTER_SHEET_PROMPT = 
  `Character turnaround master model sheet for news anchor maxDotAi (official presenter of NeuralStories News). ` +
  `Neutral plain solid medium studio gray background (#555555), crisp high key studio lighting. ` +
  `Strictly exactly THREE panels in a horizontal 16:9 layout: ` +
  `1. Left panel: Large front face portrait closeup with smart black rectangular glasses, short styled dark hair, neat short beard, looking confidently into the camera. ` +
  `2. Center panel: Frontal body view framed strictly from clavicles down to waist, showing precise matching dark navy tailored tech blazer and minimalist inner shirt. NO HEAD/NO FACE in this panel. ` +
  `3. Right panel: Posterior rear back view of the upper torso and head from behind, identical clothing and posture. NO FRONT FACE. ` +
  `Strict rule: exactly ONE visible face in the entire 16:9 canvas. Zero duplication, photorealistic 8k, broadcast production sheet.`;

export const BACKGROUND_PRESETS: BackgroundPreset[] = [
  {
    id: 'crt_original_wide',
    title: 'Estudio CRT Clásico (16:9)',
    description: 'Batería de monitores de tubo CRT retroiluminados, estética cyberpunk corporativa cálida',
    aspectRatio: '16:9',
    promptDescriptor: 'Original NeuralStories studio setup with vintage physical cathode-ray tube (CRT) monitor wall, glowing amber and cyan scanlines, physical bezel hardware monitors, subtle broadcast studio depth of field.'
  },
  {
    id: 'crt_original_vertical',
    title: 'Estudio CRT Vertical (9:16)',
    description: 'Encuadre optimizado para móviles/Reels/TikTok con torres verticales de pantallas CRT',
    aspectRatio: '9:16',
    promptDescriptor: 'Vertical 9:16 format broadcasting backdrop with stacked physical CRT cathode televisions, raster beam scanlines, moody newsroom lighting, dark reflections.'
  },
  {
    id: 'crt_glitch_accent',
    title: 'Estudio CRT con Alerta Glitch',
    description: 'Fondo de pantallas CRT parpadeando con gráficos de datos y matrices de noticias',
    aspectRatio: '16:9',
    promptDescriptor: 'CRT monitor studio bank showing live AI breaking news graphics, faint analog sync glitch, warm tube filament glow behind the anchor.'
  }
];

export const ALGENIB_VOICE_CONFIG: VoiceConfig = {
  profile: 'Algenib',
  gender: 'Masculina',
  timbre: 'Grave, ligeramente rugosa, con peso editorial y calidez radiofónica',
  locale: 'Español de España (Castellano neutro ibérico)',
  speedMultiplier: 1.18, // 18% más rápido
  cadenceDescription: 'Locución dinámica, dicción impecable, ritmo picado continuo sin titubeos ni silencios muertos, tono informativo enérgico pero riguroso.'
};

export const CAMERA_MOVEMENTS_CATALOG: CameraMovement[] = [
  {
    id: 'lateral_slide_in',
    label: 'Entrada Lateral Rápida (Whip-in)',
    category: 'dinamismo',
    description: 'Cámara entra desde la izquierda/derecha y clava el encuadre en el presentador.',
    promptInstruction: 'Rapid smooth lateral camera whip-in from screen left to center lock-on, anchor remains rock steady.',
    selected: true
  },
  {
    id: 'chest_punch_zoom',
    label: 'Zoom Rápido al Pecho (Snap Zoom)',
    category: 'encuadre',
    description: 'Encuadre cerrado desde el pecho con empuje óptico dinámico.',
    promptInstruction: 'Tight chest-up close framing, immediate punchy snap-zoom toward anchor chest, broadcast telemetry stability.',
    selected: true
  },
  {
    id: 'subtle_dolly',
    label: 'Travelling Frontal Continuo',
    category: 'dinamismo',
    description: 'Acercamiento progresivo constante de 8 segundos sin sacudidas.',
    promptInstruction: 'Continuous slow push-in dolly shot toward speaker face for 8 seconds, zero camera shake.',
    selected: false
  },
  {
    id: 'rgb_glitch_cut',
    label: 'Transición Glitch RGB Analógico',
    category: 'efecto',
    description: 'Aberración cromática analógica y micro desfase horizontal sin afectar al personaje.',
    promptInstruction: 'Subtle high-speed RGB channel split chromatic aberration glitch, analog VHS raster shift flash for 0.4s.',
    selected: true
  },
  {
    id: 'horizontal_flip',
    label: 'Inversión de Ángulo / Panorámica Rápida',
    category: 'encuadre',
    description: 'Cambio de perspectiva lateral a frontal en corte de compás.',
    promptInstruction: 'Dynamic perspective shift snapping from 15-degree off-axis angle to dead-center frontal anchor posture.',
    selected: false
  }
];

export const INITIAL_VISUAL_REFERENCES: VisualReferenceItem[] = [
  {
    id: 'ref-char-01',
    refType: 'audiovisual',
    name: 'maxDotAi - Retrato Frontal Canónico',
    identifier: 'REF-CHAR-01',
    category: 'personaje',
    imageUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=600&q=80',
    description: 'Rostro masculino mediterráneo, gafas de montura negra rectangular, barba corta perfilada de 3 días, mirada frontal directa al teleprómpter.',
    version: 'v1.4',
    status: 'pendiente',
    selectedForPrompt: false,
    isEpisodePermanent: true,
    tags: ['maxdotai', 'gafas_negras', 'rostro', 'canónico'],
    createdAt: '2025-02-01'
  },
  {
    id: 'ref-bg-01',
    refType: 'audiovisual',
    name: 'Muro CRT Analógico Original',
    identifier: 'REF-BG-CRT-01',
    category: 'fondo',
    imageUrl: 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=600&q=80',
    description: 'Pared de monitores de tubo catódico con curvas de vidrio, biseles metálicos, fósforo ámbar y cian, líneas de barrido entrelazadas.',
    version: 'v2.1',
    status: 'pendiente',
    selectedForPrompt: false,
    isEpisodePermanent: true,
    tags: ['crt', 'scanlines', 'plató', 'ámbar'],
    createdAt: '2025-02-05'
  },
  {
    id: 'ref-scene-01',
    refType: 'audiovisual',
    name: 'Encuadre Cerrado al Pecho 8s',
    identifier: 'REF-SCENE-CHEST-01',
    category: 'escena',
    imageUrl: 'https://images.unsplash.com/photo-1492691527719-9d1e07e534b4?auto=format&fit=crop&w=600&q=80',
    description: 'Composición clásica de presentador de noticias de alta tecnología: encuadre de busto desde el pecho, iluminación lateral y silueteado cian.',
    version: 'v1.0',
    status: 'pendiente',
    selectedForPrompt: false,
    isEpisodePermanent: false,
    tags: ['encuadre', 'pecho', 'televisivo', '8s'],
    createdAt: '2025-02-10'
  },
  {
    id: 'ref-style-01',
    refType: 'audiovisual',
    name: 'Estética Editorial Neocibernética',
    identifier: 'REF-STYLE-CYBER-01',
    category: 'estilo',
    imageUrl: 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=600&q=80',
    description: 'Acabado broadcast sin estridencias, grano cinematográfico sutil de 35mm, aberración cromática calibrada y contraste cromático ámbar/azul noche.',
    version: 'v1.2',
    status: 'pendiente',
    selectedForPrompt: false,
    isEpisodePermanent: false,
    tags: ['estilo', 'broadcast', 'grano', 'neuralstories'],
    createdAt: '2025-02-12'
  }
];

export const INITIAL_EDITORIAL_REFERENCES: EditorialReferenceItem[] = [
  {
    id: 'ed-src-01',
    refType: 'editorial',
    identifier: 'ED-SRC-01',
    title: 'Paper Técnico: Escalabilidad de Inferencia en Tiempo Real',
    sourceType: 'documento',
    urlOrCitation: 'https://arxiv.org/abs/2412.inference-scaling-demo',
    summaryOrExcerpt: 'Demostración de destilación de modelos de difusión capaces de computar batches de vídeo a 60 fps sin drift perceptual.',
    authorOrChannel: 'MIT Computer Science & AI Lab',
    status: 'pendiente',
    createdAt: '2025-02-14'
  },
  {
    id: 'ed-src-02',
    refType: 'editorial',
    identifier: 'ED-SRC-02',
    title: 'Transcripción: Conferencia de Líderes de Chips Cuánticos',
    sourceType: 'transcripcion_youtube',
    urlOrCitation: 'https://youtube.com/watch?v=neural_keynote_transcription',
    summaryOrExcerpt: 'Declaración clave: Los centros de datos europeos adoptan arquitecturas híbridas neuromórficas para el segundo semestre.',
    authorOrChannel: 'TechSummit Global Stream',
    status: 'pendiente',
    createdAt: '2025-02-18'
  },
  {
    id: 'ed-src-03',
    refType: 'editorial',
    identifier: 'ED-SRC-03',
    title: 'Comunicado Regulatorio: Estándares de Consistencia en Medios Sintéticos',
    sourceType: 'comunicado_oficial',
    urlOrCitation: 'https://europa.eu/ai-act/broadcast-synthetic-guidelines',
    summaryOrExcerpt: 'Obligatoriedad de trazabilidad de semillas de identidad para presentadores de noticias sintéticos en territorio de la UE.',
    authorOrChannel: 'Oficina Europea de Inteligencia Artificial',
    status: 'pendiente',
    createdAt: '2025-02-20'
  }
];

export const INITIAL_NEWS_ARTICLES: NewsArticle[] = [
  {
    id: 'news-001',
    title: 'Avance en Inferencia de Modelos Multimodales en Tiempo Real',
    summary: 'Nuevas arquitecturas reducen drásticamente la latencia en el razonamiento de agentes autónomos con despliegue en Europa.',
    fullScript: 'Bienvenidos a NeuralStories News. Soy maxDotAi. Una nueva filtración revela arquitecturas que razonan en tiempo real sin latencia perceptible. Los ingenieros confirman la integración total en agentes autónomos antes del próximo trimestre. Este avance permite interacciones fluidas sin tiempos de espera.',
    date: '2025-02-22',
    verificationStatus: 'sin_verificar',
    approvalStatus: 'pendiente',
    episodeBlock: 'Bloque 1: Titulares Principales',
    orderIndex: 1,
    sources: ['https://arxiv.org/abs/2412.inference-scaling-demo', 'https://neural.news/internal-brief-01'],
    editorialReferenceIds: ['ED-SRC-01'],
    visualReferenceIds: ['REF-CHAR-01', 'REF-BG-CRT-01', 'REF-STYLE-CYBER-01'],
    tags: ['ia', 'multimodal', 'agentes', 'hardware'],
    metadata: {
      importedFrom: 'api_sync',
      verifiedBy: 'Equipo Editorial neural.news'
    }
  },
  {
    id: 'news-002',
    title: 'Estándares Europeos de Trazabilidad en Presentadores Sintéticos',
    summary: 'La normativa comunitaria fija la obligatoriedad de sellos y hojas de consistencia para avatares periodísticos.',
    fullScript: 'La Oficina Europea de Inteligencia Artificial aprueba las primeras directrices para presentadores sintéticos. A partir de este año, todo noticiero automatizado deberá conservar hojas maestras de identidad inmutables para evitar suplantaciones y garantizar la transparencia editorial ante la audiencia.',
    date: '2025-02-21',
    verificationStatus: 'sin_verificar',
    approvalStatus: 'pendiente',
    episodeBlock: 'Bloque 1: Titulares Principales',
    orderIndex: 2,
    sources: ['https://europa.eu/ai-act/broadcast-synthetic-guidelines'],
    editorialReferenceIds: ['ED-SRC-03'],
    visualReferenceIds: ['REF-CHAR-01', 'REF-BG-CRT-01'],
    tags: ['regulacion', 'ue', 'avatares', 'etica'],
    metadata: {
      importedFrom: 'manual',
      verifiedBy: 'Mesa de Fact-Checking'
    }
  },
  {
    id: 'news-003',
    title: 'Consistencia Temporal Cinematográfica a 60 FPS en Modelos de Vídeo',
    summary: 'Se superan las aberraciones visuales y el morphing en planos secuencia largos gracias a matrices de atención física.',
    fullScript: 'La consistencia temporal en modelos generativos supera el listón cinematográfico más estricto. La iluminación física, la ausencia de deformaciones faciales y las físicas de partículas estables a sesenta fotogramas marcan el inicio de una nueva era en la producción audiovisual.',
    date: '2025-02-20',
    verificationStatus: 'en_revision',
    approvalStatus: 'pendiente',
    episodeBlock: 'Bloque 2: Tendencias Audiovisuales',
    orderIndex: 3,
    sources: ['https://neural.news/tech-radar-2025'],
    editorialReferenceIds: ['ED-SRC-02'],
    visualReferenceIds: ['REF-STYLE-CYBER-01'],
    tags: ['video-ia', 'consistencia', '60fps'],
    metadata: {
      importedFrom: 'manual'
    }
  }
];

export const INITIAL_EPISODE_BLOCKS: ProductionEpisodeBlock[] = [
  {
    id: 'block-01',
    title: 'Bloque 1: Titulares Principales',
    date: '2025-02-22',
    articleIds: ['news-001', 'news-002'],
    permanentVisualRefIds: ['REF-CHAR-01', 'REF-BG-CRT-01'],
    notes: 'Emisión central de apertura con maxDotAi en mesa CRT principal.'
  },
  {
    id: 'block-02',
    title: 'Bloque 2: Tendencias Audiovisuales',
    date: '2025-02-22',
    articleIds: ['news-003'],
    permanentVisualRefIds: ['REF-CHAR-01', 'REF-BG-CRT-01'],
    notes: 'Bloque de profundidad tecnológica e impacto en industrias creativas.'
  }
];

export const BATCH_5_NEWS_SAMPLE: NewsArticle[] = [
  {
    id: 'batch-01',
    title: 'Nuevos Aceleradores Fotónicos Reducen Consumo Energético en Datacenters',
    summary: 'Consorcio europeo prueba chips basados en luz para inferencia masiva con 85% menos de calor disipado.',
    fullScript: 'Nuevos procesadores fotónicos logran ejecutar modelos masivos reduciendo el consumo eléctrico en un ochenta y cinco por ciento. Los centros de computación de Fráncfort inician su implementación industrial esta misma semana.',
    date: '2025-02-22',
    verificationStatus: 'sin_verificar',
    approvalStatus: 'pendiente',
    episodeBlock: 'Bloque 1: Titulares Principales',
    orderIndex: 4,
    sources: ['https://nature.com/articles/photonics-energy-2025'],
    editorialReferenceIds: ['ED-SRC-01'],
    visualReferenceIds: ['REF-CHAR-01', 'REF-BG-CRT-01'],
    tags: ['hardware', 'fotónica', 'sostenibilidad']
  },
  {
    id: 'batch-02',
    title: 'Sistemas de Audio Generativo Eliminan Latencia en Traducción Simultánea',
    summary: 'Voz y clonación tímbrica operan por debajo de 120 milisegundos en conferencias internacionales.',
    fullScript: 'La interpretación simultánea con inteligencia artificial alcanza latencias inferiores a ciento veinte milisegundos. Diplomáticos y cadenas de noticias comienzan a utilizar doblaje de voz sincronizado en tiempo real.',
    date: '2025-02-22',
    verificationStatus: 'sin_verificar',
    approvalStatus: 'pendiente',
    episodeBlock: 'Bloque 1: Titulares Principales',
    orderIndex: 5,
    sources: ['https://neural.news/audio-realtime-breakthrough'],
    editorialReferenceIds: ['ED-SRC-02'],
    visualReferenceIds: ['REF-CHAR-01', 'REF-BG-CRT-01'],
    tags: ['audio', 'algenib', 'traduccion']
  },
  {
    id: 'batch-03',
    title: 'Alianza Estratégica en Medios Abiertos para Certificación de Origen',
    summary: 'Agencias mundiales adoptan metadatos C2PA en todas las secuencias sintéticas distribuidas.',
    fullScript: 'Las principales agencias informativas internacionales adoptan el estándar de procedencia C2PA de forma obligatoria. Cada fotograma generado llevará una firma criptográfica verificable por cualquier usuario.',
    date: '2025-02-21',
    verificationStatus: 'sin_verificar',
    approvalStatus: 'pendiente',
    episodeBlock: 'Bloque 2: Tendencias Audiovisuales',
    orderIndex: 6,
    sources: ['https://c2pa.org/standards-announcement'],
    editorialReferenceIds: ['ED-SRC-03'],
    visualReferenceIds: ['REF-STYLE-CYBER-01'],
    tags: ['c2pa', 'seguridad', 'procedencia']
  },
  {
    id: 'batch-04',
    title: 'Despliegue de Redes Celulares 5G Autónomas para Transmisiones IA',
    summary: 'Operadores habilitan canales prioritarios con QoS garantizado para unidades móviles de telemetría sintética.',
    fullScript: 'Las cadenas de televisión desplegarán unidades de emisión móvil conectadas a redes celulares privadas. Esto garantiza la subida continua de flujos audiovisuales sin cortes ni pérdida de calidad.',
    date: '2025-02-20',
    verificationStatus: 'en_revision',
    approvalStatus: 'pendiente',
    episodeBlock: 'Bloque 2: Tendencias Audiovisuales',
    orderIndex: 7,
    sources: ['https://telecom-news.eu/5g-broadcast-slice'],
    editorialReferenceIds: [],
    visualReferenceIds: ['REF-BG-CRT-01'],
    tags: ['5g', 'infraestructura', 'movil']
  },
  {
    id: 'batch-05',
    title: 'Repositorios Abiertos de Pesos Estables Superan las 50 Millones de Descargas',
    summary: 'La comunidad de código abierto lidera la adopción de herramientas creativas y pipelines locales.',
    fullScript: 'Los modelos abiertos de generación visual alcanzan un nuevo récord histórico con cincuenta millones de descargas mensuales. Los estudios independientes consolidan su independencia tecnológica.',
    date: '2025-02-19',
    verificationStatus: 'sin_verificar',
    approvalStatus: 'pendiente',
    orderIndex: 8,
    sources: ['https://huggingface.co/blog/open-weights-milestone'],
    editorialReferenceIds: [],
    visualReferenceIds: [],
    tags: ['open-source', 'huggingface', 'comunidad']
  }
];

export const SAMPLE_NEWS_SCRIPTS = [
  {
    title: 'Avance de Modelos Multimodales',
    text: 'Nueva filtración revela arquitecturas que razonan en tiempo real sin latencia perceptible. Los ingenieros confirman integración total en agentes autónomos antes del próximo trimestre.'
  },
  {
    title: 'Hitos en Síntesis de Vídeo',
    text: 'La consistencia temporal en modelos generativos supera el listón cinematográfico: iluminación física, sin morphing facial y con físicas de partículas estables a 60 fotogramas.'
  },
  {
    title: 'NeuralStories Titular Flash',
    text: 'Bienvenidos a NeuralStories News. Soy maxDotAi. Hoy analizamos el salto generativo que redefine la producción de medios sintéticos en Europa.'
  }
];