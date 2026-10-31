import { NewsArticle } from '../types';

export interface DuplicateMatchResult {
  isDuplicate: boolean;
  reason?: 'id_match' | 'source_match' | 'title_similarity' | 'slug_match';
  matchedArticleId?: string;
  matchedTitle?: string;
  similarityScore?: number;
  details?: string;
}

/**
 * Normaliza URLs de fuentes eliminando parámetros de seguimiento y trailing slashes.
 */
function normalizeUrl(url: string): string {
  try {
    const clean = url.trim().toLowerCase();
    const u = new URL(clean);
    // Eliminar parámetros analíticos típicos
    u.searchParams.delete('utm_source');
    u.searchParams.delete('utm_medium');
    u.searchParams.delete('utm_campaign');
    u.searchParams.delete('si'); // Youtube tracking
    return (u.origin + u.pathname).replace(/\/+$/, '');
  } catch {
    return url.trim().toLowerCase().replace(/\/+$/, '');
  }
}

/**
 * Extrae conjunto de n-gramas de palabras para cálculo de similitud.
 */
function getWordTokens(text: string): Set<string> {
  const words = text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // Quitar tildes
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter(w => w.length > 2); // Palabras significativas (>2 caracteres)
  return new Set(words);
}

/**
 * Coeficiente de similitud de Jaccard entre dos cadenas.
 */
function calculateJaccardSimilarity(textA: string, textB: string): number {
  const setA = getWordTokens(textA);
  const setB = getWordTokens(textB);
  if (setA.size === 0 || setB.size === 0) return 0;

  let intersection = 0;
  for (const token of setA) {
    if (setB.has(token)) intersection++;
  }

  const union = new Set([...setA, ...setB]).size;
  return union > 0 ? intersection / union : 0;
}

/**
 * Evalúa si una noticia candidata ya existe en la colección activa
 * considerando ID/UUID y URL canónica/fuente primero (capa canónica) y, solo
 * después, similitud léxica de titular (heurística Jaccard: NUNCA equivale a
 * misma noticia; el resultado exige revisión humana y expone su puntuación).
 */
export function checkArticleDuplicate(
  candidate: Partial<NewsArticle>,
  existingArticles: NewsArticle[],
  similarityThreshold = 0.65
): DuplicateMatchResult {
  const candId = candidate.id?.trim().toLowerCase();
  const candUuid = candidate.uuid?.trim().toLowerCase();
  const candSlug = candidate.slug?.trim().toLowerCase();
  const candTitle = candidate.title?.trim() || '';
  const candSources = (candidate.sources || []).map(normalizeUrl).filter(s => s.length > 0);

  for (const existing of existingArticles) {
    // 1. Detección por Identificador / UUID / ExternalId
    const exId = existing.id.trim().toLowerCase();
    const exUuid = existing.uuid?.trim().toLowerCase();
    const exSlug = existing.slug?.trim().toLowerCase();
    const exExtId = existing.metadata?.externalId?.trim().toLowerCase();
    const candExtId = candidate.metadata?.externalId?.trim().toLowerCase();

    if (candId && candId === exId) {
      return {
        isDuplicate: true,
        reason: 'id_match',
        matchedArticleId: existing.id,
        matchedTitle: existing.title,
        details: `Identificador primario idéntico: ${existing.id}`
      };
    }

    if (candUuid && exUuid && candUuid === exUuid) {
      return {
        isDuplicate: true,
        reason: 'id_match',
        matchedArticleId: existing.id,
        matchedTitle: existing.title,
        details: `UUID editorial coincidente: ${existing.uuid}`
      };
    }

    if (candExtId && exExtId && candExtId === exExtId) {
      return {
        isDuplicate: true,
        reason: 'id_match',
        matchedArticleId: existing.id,
        matchedTitle: existing.title,
        details: `Identificador externo de backend duplicado: ${exExtId}`
      };
    }

    if (candSlug && exSlug && candSlug === exSlug) {
      return {
        isDuplicate: true,
        reason: 'slug_match',
        matchedArticleId: existing.id,
        matchedTitle: existing.title,
        details: `Slug coincidente: ${existing.slug}`
      };
    }

    // 2. Detección por Fuente Canónica (URLs normalizadas de YouTube, Spotify, Arxiv, artículos)
    if (candSources.length > 0 && existing.sources && existing.sources.length > 0) {
      const exSources = existing.sources.map(normalizeUrl);
      const sharedSource = candSources.find(cs => exSources.includes(cs));
      if (sharedSource) {
        return {
          isDuplicate: true,
          reason: 'source_match',
          matchedArticleId: existing.id,
          matchedTitle: existing.title,
          details: `Coincidencia exacta de fuente URL: ${sharedSource}`
        };
      }
    }

    // 3. Detección por Similitud de Texto (Jaccard sobre titular y resumen)
    if (candTitle && existing.title) {
      const score = calculateJaccardSimilarity(candTitle, existing.title);
      if (score >= similarityThreshold) {
        return {
          isDuplicate: true,
          reason: 'title_similarity',
          matchedArticleId: existing.id,
          matchedTitle: existing.title,
          similarityScore: Number((score * 100).toFixed(1)),
          details: `Similitud léxica elevada (${(score * 100).toFixed(0)}%) con "${existing.title}"`
        };
      }
    }
  }

  return { isDuplicate: false };
}