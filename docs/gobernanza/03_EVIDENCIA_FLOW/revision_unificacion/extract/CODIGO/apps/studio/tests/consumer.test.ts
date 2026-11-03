/**
 * Pruebas del consumidor del contrato production_handoff.v1 en Studio.
 * Ejecución: `npm test` (Node 24 con eliminación de tipos nativa).
 * Reutiliza los fixtures canónicos de `fixtures/handoff/` y comprueba que la
 * copia del esquema embebida coincide con el canon de `packages/contracts/`.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

import {
  DuplicateHandoffError,
  HandoffValidationError,
  importHandoff,
  loadRegistry,
  memoryStore,
  storyToArticle,
} from '../src/lib/handoffConsumer.ts';

const STUDIO_ROOT = fileURLToPath(new URL('..', import.meta.url));
const REPO_ROOT = fileURLToPath(new URL('../../..', import.meta.url));

const schema = JSON.parse(
  readFileSync(`${STUDIO_ROOT}/src/contracts/production_handoff.v1.schema.json`, 'utf-8')
);
const canonicalSchema = JSON.parse(
  readFileSync(`${REPO_ROOT}/packages/contracts/production_handoff.v1.schema.json`, 'utf-8')
);

function fixture(name: string): unknown {
  return JSON.parse(readFileSync(`${REPO_ROOT}/fixtures/handoff/${name}`, 'utf-8'));
}

let passed = 0;
async function test(name: string, fn: () => Promise<void> | void) {
  await fn();
  passed++;
  console.log(`✔ ${name}`);
}

await test('la copia del esquema embebida es idéntica al canon de packages/contracts', () => {
  assert.deepEqual(schema, canonicalSchema);
});

await test('acepta el fixture single válido y lo mapea a noticia aprobada', async () => {
  const store = memoryStore();
  const result = await importHandoff(fixture('single_valid.json'), { schema, store });
  assert.equal(result.mode, 'single');
  assert.equal(result.articles.length, 1);
  const article = result.articles[0];
  assert.equal(article.approvalStatus, 'aprobada');
  assert.equal(article.verificationStatus, 'verificado');
  assert.ok(article.fullScript.includes('modelos de lenguaje'));
  assert.ok(article.sources.length >= 3);
  assert.ok(loadRegistry(store).some((e) => e.handoff_id === result.handoffId));
});

await test('acepta el lote de cinco noticias', async () => {
  const result = await importHandoff(fixture('batch5_valid.json'), {
    schema,
    store: memoryStore(),
  });
  assert.equal(result.mode, 'batch');
  assert.equal(result.articles.length, 5);
});

await test('rechaza un guion manipulado aunque el esquema sea válido', async () => {
  await assert.rejects(
    () => importHandoff(fixture('schema_valid_tampered_hash.json'), { schema, store: memoryStore() }),
    HandoffValidationError
  );
});

await test('rechaza documentos que no cumplen el contrato', async () => {
  for (const name of [
    'invalid_not_approved.json',
    'invalid_batch3.json',
    'invalid_source_without_identifier.json',
  ]) {
    await assert.rejects(
      () => importHandoff(fixture(name), { schema, store: memoryStore() }),
      HandoffValidationError,
      `${name} debía rechazarse`
    );
  }
});

await test('rechaza reimportar el mismo traspaso', async () => {
  const store = memoryStore();
  const doc = fixture('single_valid.json');
  await importHandoff(doc, { schema, store });
  await assert.rejects(
    () => importHandoff(doc, { schema, store }),
    DuplicateHandoffError
  );
});

await test('rechaza la misma noticia y revisión dentro de otro traspaso', async () => {
  const store = memoryStore();
  const first = fixture('single_valid.json');
  const second = JSON.parse(JSON.stringify(first));
  (second as { handoff_id: string }).handoff_id = (first as { handoff_id: string }).handoff_id + '-variante';
  await importHandoff(first, { schema, store });
  await assert.rejects(
    () => importHandoff(second, { schema, store }),
    DuplicateHandoffError
  );
});

await test('las fuentes sin URL se etiquetan como manuales sin inventar enlaces', () => {
  const story = fixture('single_valid.json') as { stories: Array<Record<string, unknown>> };
  const article = storyToArticle(story.stories[0] as never, 'prueba');
  const manual = article.sources.find((s) => s.startsWith('manual:'));
  assert.ok(manual, 'la fuente manual debe conservar un identificador sin URL');
  assert.ok(article.sources.some((s) => s.startsWith('https://')));
});

console.log(`\n${passed} pruebas del consumidor Studio en verde.`);
