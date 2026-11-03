/**
 * Pruebas del proyecto de producción audiovisual (Fase 4, T405-T411).
 * Ejecución: `npm test` (Node 24). Comprueba perfiles versionados, plan
 * determinista de escenas, biblioteca de prompts, ediciones versionadas,
 * consistencia y registro de versiones.
 */
import assert from 'node:assert/strict';

import { NEURALNEWS_CANON_PROFILE, findProfile, studioPresetForFormat } from '../src/data/avProfiles.ts';
import {
  applySceneEdit,
  checkConsistency,
  createProductionProject,
  exportProjectJson,
  loadProjectVersions,
  memoryStore,
  saveProjectVersion,
} from '../src/lib/productionProject.ts';

const ARTICLE = {
  id: 'news-test-1',
  title: 'Noticia de prueba del plan de producción',
  fullScript:
    'Buenas tardes, hoy analizamos tres avances recientes en modelos de lenguaje abiertos. ' +
    'Primero: las técnicas de destilación han reducido el coste de inferencia de los modelos pequeños, y varios laboratorios han publicado resultados comparables con una fracción de los parámetros. ' +
    'En segundo lugar, la comunidad ha empezado a estandarizar pruebas de eficiencia energética, un paso clave para comparar sistemas de forma transparente y reproducible entre laboratorios. ' +
    'Además, los nuevos marcos de evaluación permiten medir la deriva de los modelos a lo largo del tiempo con métricas compartidas por toda la industria. ' +
    'Y para cerrar: la transparencia y la trazabilidad serán la clave del próximo año. Esto ha sido NeuralStories News.',
};

let passed = 0;
async function test(name: string, fn: () => Promise<void> | void) {
  await fn();
  passed++;
  console.log(`✔ ${name}`);
}

await test('el perfil canon está versionado y es registrable', () => {
  const profile = findProfile('neuralnews-canon-v1');
  assert.ok(profile, 'el perfil canon debe existir en el registro');
  assert.match(profile!.version, /^\d+\.\d+\.\d+$/);
  assert.equal(profile!.character.id, 'neuraldotai');
  assert.equal(profile!.character.assetsLicensed, false, 'los recursos no están licenciados: debe quedar registrado');
  assert.ok(profile!.limitations.length > 0);
  assert.equal(findProfile('otro-perfil'), undefined);
});

await test('el fondo del estudio depende del formato de salida', () => {
  assert.equal(studioPresetForFormat(NEURALNEWS_CANON_PROFILE, '9:16').id, 'crt_original_vertical');
  assert.equal(studioPresetForFormat(NEURALNEWS_CANON_PROFILE, '16:9').id, 'crt_original_wide');
});

await test('crea un plan reproducible con escenas, prompts y encuadres', () => {
  const project = createProductionProject(ARTICLE, NEURALNEWS_CANON_PROFILE, { outputFormat: '9:16' });
  assert.ok(project.scenes.length >= 3, 'el guion debe dividirse en varias escenas');
  assert.equal(project.scenes[0].sceneType, 'apertura');
  assert.equal(project.scenes[project.scenes.length - 1].sceneType, 'cierre');
  for (const scene of project.scenes) {
    assert.ok(scene.scriptSnippet.trim(), `escena ${scene.sceneIndex} sin locución`);
    assert.ok(scene.imagePrompt.includes('NeuralDotAI'), 'el prompt debe incluir la identidad del personaje');
    assert.ok(scene.imagePrompt.includes('CRT'), 'el prompt debe incluir el plató CRT');
    assert.ok(scene.framing.includes('pecho'), 'encuadre canon desde el pecho');
  }
  assert.ok(project.warnings.length === 0, `sin avisos de consistencia: ${project.warnings.join('; ')}`);
  // Determinismo: dos creaciones con las mismas entradas producen el mismo plan
  // (se excluye la marca temporal de creación).
  const stripDate = (json: string) => json.replace(/"createdAt":\s*"[^"]*"/, '');
  const again = createProductionProject(ARTICLE, NEURALNEWS_CANON_PROFILE, { outputFormat: '9:16' });
  assert.equal(stripDate(exportProjectJson(project)), stripDate(exportProjectJson(again)));
});

await test('la edición de escenas crea una copia inmutable con versión nueva', () => {
  const project = createProductionProject(ARTICLE, NEURALNEWS_CANON_PROFILE);
  const edited = applySceneEdit(project, 1, { scriptSnippet: 'Locución ajustada a mano.' });
  assert.notEqual(edited, project);
  assert.equal(edited.planVersion, project.planVersion + 1);
  assert.equal(edited.scenes[0].scriptSnippet, 'Locución ajustada a mano.');
  assert.equal(project.scenes[0].scriptSnippet, project.scenes[0].scriptSnippet, 'el original no se muta');
});

await test('guarda y recupera versiones del plan por proyecto', () => {
  const store = memoryStore();
  const project = createProductionProject(ARTICLE, NEURALNEWS_CANON_PROFILE);
  const edited = applySceneEdit(project, 1, { imagePrompt: 'Prompt revisado por producción.' });
  saveProjectVersion(project, store);
  saveProjectVersion(edited, store);
  const versions = loadProjectVersions(project.projectId, store);
  assert.equal(versions.length, 2);
  assert.equal(versions[0].planVersion, 1);
  assert.equal(versions[1].planVersion, 2);
  assert.equal(versions[1].project.scenes[0].imagePrompt, 'Prompt revisado por producción.');
});

await test('la verificación de consistencia detecta planes rotos', () => {
  const project = createProductionProject(ARTICLE, NEURALNEWS_CANON_PROFILE);
  // Plan roto a mano: la edición en blanco es ignorada por diseño (no borra escenas).
  const broken = {
    ...project,
    scenes: project.scenes.map((s) => (s.sceneIndex === 1 ? { ...s, scriptSnippet: '' } : s)),
  };
  const result = checkConsistency(broken, NEURALNEWS_CANON_PROFILE);
  assert.equal(result.ok, false);
  assert.ok(result.warnings.some((w) => w.includes('locución')), 'debe avisar de escena sin locución');
  const wrongProfile = { ...broken, profileId: 'perfil-inexistente' };
  const result2 = checkConsistency(wrongProfile, NEURALNEWS_CANON_PROFILE);
  assert.ok(result2.warnings.some((w) => w.includes('perfil')));
});

console.log(`\n${passed} pruebas del plan de producción en verde.`);
