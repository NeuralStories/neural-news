/**
 * Extracción del mensaje de un error capturado sin recurrir a `any`.
 *
 * Equivale a `err.message` en el caso habitual (`Error`), pero devuelve
 * `undefined` cuando el valor lanzado no lleva mensaje, de modo que los
 * mensajes de reserva (`err.message || 'fallback'`) se mantengan igual.
 */
export function errorMessage(err: unknown): string | undefined {
  if (typeof err !== 'object' || err === null || !('message' in err)) return undefined;
  const message = (err as { message?: unknown }).message;
  if (message === undefined || message === null) return undefined;
  return String(message);
}
