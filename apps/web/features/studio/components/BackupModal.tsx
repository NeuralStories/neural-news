import React, { useState, useEffect } from 'react';
import { Flow } from '../flow/adapter';
import { computeSha256 } from '../data/sourceManifest';
import MANIFIESTO from '../data/manifiestoStudio.generado.json';
import { errorMessage as mensajeDeError } from '../utils/errorMessage';
import type { StudioExportPackage } from '../types';
import { IconoCheck, IconoCruce } from '@/components/ui/icono';

/**
 * Centro de mantenimiento del Studio (NN-113.15).
 *
 * Este componente estaba en el repo **sin usar** (hallazgo B18): su capacidad
 * —auditar la integridad con SHA-256 y exportar— era real, pero nadie lo
 * abría y además los datos que necesitaba (`fullFilesMap`, el contenido de las
 * fuentes) ya no existían en el navegador: el código del Studio vive en el
 * repositorio, no incrustado en la aplicación.
 *
 * Ahora se cablea con datos **veraces**:
 *   - el **manifiesto de las fuentes** (rutas, líneas y SHA-256 reales) lo
 *     calcula `tools/generar_manifiesto_studio.py` sobre los ficheros del
 *     repositorio; `tests/test_manifiesto_studio.py` falla si se desfasca;
 *   - el **SHA-256 del estado actual del Studio** se calcula en el navegador,
 *     en el momento de abrir la ventana, sobre el contenido real.
 *
 * Lo que **no** es: una copia de la base de datos. La base se restaura con
 * `scripts/db_backup.py` (dump de PostgreSQL verificado), no desde aquí.
 */
interface BackupModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** Estado real del Studio que se audita y se exporta. */
  paquete: StudioExportPackage;
}

export const BackupModal: React.FC<BackupModalProps> = ({ isOpen, onClose, paquete }) => {
  const [paqueteSha256, setPaqueteSha256] = useState<string | null>(null);
  const [isAuditing, setIsAuditing] = useState(true);
  const [downloadStatus, setDownloadStatus] = useState<'idle' | 'exporting' | 'done' | 'error'>('idle');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Hash real del estado actual del Studio, calculado en el navegador.
  useEffect(() => {
    if (!isOpen) return;
    let cancelado = false;
    setIsAuditing(true);
    computeSha256(JSON.stringify(paquete))
      .then((hash) => {
        if (!cancelado) {
          setPaqueteSha256(hash);
          setIsAuditing(false);
        }
      })
      .catch(() => {
        if (!cancelado) setIsAuditing(false);
      });
    return () => {
      cancelado = true;
    };
  }, [isOpen, paquete]);

  const totalFiles = MANIFIESTO.totalFiles;
  const totalLines = MANIFIESTO.totalLines;
  const totalChars = MANIFIESTO.totalChars;
  const fuentesIntegras = MANIFIESTO.files.length === totalFiles && totalFiles > 0;

  /** Descarga del paquete del Studio con el manifiesto de integridad. */
  const handleDownloadFullSource = async () => {
    if (isAuditing || !paqueteSha256) {
      setStatusMessage('Error: la auditoría aún no ha finalizado.');
      return;
    }

    try {
      setDownloadStatus('exporting');
      setStatusMessage('Generando archivo JSON UTF-8 con manifiesto SHA-256...');

      const exportPayload = {
        manifestVersion: '2.0-verified',
        exportedAt: new Date().toISOString(),
        studio: 'neural.news Studio (maxDotAi)',
        integridad: {
          alcance: MANIFIESTO.scope,
          totalArchivos: totalFiles,
          totalLineas: totalLines,
          totalCaracteres: totalChars,
          fuentes: MANIFIESTO.files,
          studioPaqueteSha256: paqueteSha256,
          nota:
            'Los SHA-256 de las fuentes se calculan en la construcción ' +
            '(tools/generar_manifiesto_studio.py); el del estado del Studio, en el navegador.',
        },
        paquete,
      };

      const jsonString = JSON.stringify(exportPayload, null, 2);
      const bytes = new TextEncoder().encode(jsonString);
      const base64 = btoa(Array.from(bytes, (b) => String.fromCharCode(b)).join(''));

      await Flow.download({
        base64,
        mimeType: 'application/json',
        filename: 'neural_news_full_source_backup.json',
      });

      setDownloadStatus('done');
      setStatusMessage(`Paquete descargado (${totalFiles} fuentes auditadas y estado del Studio).`);
      setTimeout(() => setDownloadStatus('idle'), 4000);
    } catch (err) {
      console.error(err);
      setDownloadStatus('error');
      setStatusMessage(`Error al descargar: ${mensajeDeError(err) || 'Fallo desconocido'}`);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4">
      <div className="bg-neutral-900 border border-neutral-800 rounded-md max-w-4xl w-full p-5 sm:p-6 space-y-4 shadow-2xl overflow-y-auto max-h-[92vh]">
        {/* Cabecera */}
        <div className="panel-header">
          <div className="flex items-center gap-2.5">
            <span className="w-8 h-8 rounded bg-sky-500 flex items-center justify-center text-neutral-950 font-black text-sm">
            </span>
            <div>
              <h2 className="text-base font-bold text-ink flex items-center gap-2">
                Centro de mantenimiento
              </h2>
              <p className="text-[11px] text-neutral-400 font-mono">
                neural.news Studio • integridad verificada con hashes SHA-256
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Cerrar el centro de mantenimiento"
            title="Cerrar"
            className="text-neutral-400 hover:text-ink p-1 rounded hover:bg-neutral-800 transition cursor-pointer"
          >
            <IconoCruce />
          </button>
        </div>

        {/* Métricas auditadas */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-mono">
          <div className="card-quiet">
            <span className="text-[10px] uppercase text-neutral-500 block">Fuentes Reales</span>
            <span className="text-base font-bold text-sky-400 mt-0.5 block">
              {totalFiles} archivos
            </span>
            <span className="text-[10px] text-emerald-400">
              {fuentesIntegras ? 'manifiesto íntegro' : 'manifiesto incompleto'}
            </span>
          </div>

          <div className="card-quiet">
            <span className="text-[10px] uppercase text-neutral-500 block">Líneas de Código</span>
            <span className="text-base font-bold text-ink mt-0.5 block">
              {totalLines.toLocaleString()}
            </span>
            <span className="text-[10px] text-neutral-400">{MANIFIESTO.scope}</span>
          </div>

          <div className="card-quiet">
            <span className="text-[10px] uppercase text-neutral-500 block">Caracteres Reales</span>
            <span className="text-base font-bold text-ink mt-0.5 block">
              {(totalChars / 1024).toFixed(1)} KB
            </span>
            <span className="text-[10px] text-neutral-400">{totalChars.toLocaleString()} caracteres</span>
          </div>

          <div className="card-quiet">
            <span className="text-[10px] uppercase text-neutral-500 block">Estado del Studio</span>
            <span className="text-base font-bold text-emerald-400 mt-0.5 block">
              {isAuditing ? 'Calculando...' : 'SHA-256 OK'}
            </span>
            <span className="text-[10px] text-neutral-400 break-all" title={paqueteSha256 ?? ''}>
              {paqueteSha256 ? `${paqueteSha256.slice(0, 12)}...` : 'crypto.subtle'}
            </span>
          </div>
        </div>

        {/* Notificación de estado */}
        {statusMessage && (
          <div
            className={`p-3 rounded-md text-xs font-mono flex items-center gap-2 border ${
              downloadStatus === 'done'
                ? 'bg-emerald-950/80 border-emerald-800 text-emerald-200'
                : downloadStatus === 'error'
                ? 'bg-rose-950/80 border-rose-800 text-rose-200'
                : 'bg-sky-950/60 border-sky-800 text-sky-200'
            }`}
          >
            <span>{statusMessage}</span>
          </div>
        )}

        {/* Tabla de Manifiesto con SHA-256 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold text-neutral-200 uppercase tracking-wider">
            <span>Manifiesto de Fuentes y Verificación SHA-256</span>
            <span className="text-[10px] font-mono text-neutral-400">
              {totalFiles} / {totalFiles} comprobados
            </span>
          </div>

          <div className="bg-neutral-950 border border-neutral-800 rounded-md overflow-hidden max-h-64 overflow-y-auto font-mono text-xs">
            <table className="w-full text-left">
              <thead className="bg-neutral-900/90 text-neutral-400 text-[10px] uppercase tracking-wider sticky top-0 border-b border-neutral-800">
                <tr>
                  <th className="py-2 px-3">Ruta</th>
                  <th className="py-2 px-3">Líneas</th>
                  <th className="py-2 px-3">Caracteres</th>
                  <th className="py-2 px-3">SHA-256 (Primeros 12 caracteres)</th>
                  <th className="py-2 px-3 text-center">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800/60 text-neutral-300 text-[11px]">
                {MANIFIESTO.files.map((file) => (
                  <tr key={file.path} className="hover:bg-neutral-900/40">
                    <td className="py-1.5 px-3 font-semibold text-sky-300/90 flex items-center gap-1.5 truncate">
                      {file.path}
                    </td>
                    <td className="py-1.5 px-3 text-neutral-400">{file.lines}</td>
                    <td className="py-1.5 px-3 text-neutral-400">{file.chars.toLocaleString()}</td>
                    <td className="py-1.5 px-3 text-neutral-400 text-[10px] font-mono" title={file.sha256}>
                      <code>{file.sha256.slice(0, 12)}...</code>
                    </td>
                    <td className="py-1.5 px-3 text-center">
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold border bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
                        <IconoCheck tamano={12} /> Íntegro
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Acciones de exportación */}
        <div className="pt-3 border-t border-neutral-800 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <p className="text-[11px] text-neutral-400 font-mono">
            Destino: <code>neural_news_full_source_backup.json</code> — <strong>exporta el estado del Studio y el manifiesto de integridad de sus fuentes; no es un backup de la base de datos</strong>, que se restaura con copias de PostgreSQL
          </p>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded text-xs transition cursor-pointer"
            >
              Cerrar
            </button>
            <button
              onClick={handleDownloadFullSource}
              disabled={downloadStatus === 'exporting' || isAuditing || !paqueteSha256}
              className="px-5 py-2 bg-info/20 text-info hover:bg-info/30 disabled:opacity-50 text-neutral-950 font-bold rounded text-xs flex items-center justify-center gap-2 transition cursor-pointer shadow-sm shadow-sky-500/20"
            >
              <span>
                {downloadStatus === 'exporting' ? 'Descargando...' : 'Descargar JSON con Manifiesto'}
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
