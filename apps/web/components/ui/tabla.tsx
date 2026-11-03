/**
 * Tabla densa: cabecera pegajosa, líneas de 1px, altura de fila corta y
 * cifras en monoespaciado con cifras tabulares.
 *
 * Genérica y tipada: la consola la usa para los trabajos y el resto de vistas
 * podrán reutilizarla para fuentes, noticias o lotes sin copiar el marcado.
 */
import { memo, type ReactNode } from "react";

export type Columna<T> = {
  /** Identificador estable de la columna. */
  clave: string;
  /** Texto de la cabecera. */
  cabecera: string;
  /** Contenido de la celda. */
  render: (fila: T) => ReactNode;
  /** Alineación a la derecha y cifras tabulares. */
  numerica?: boolean;
  /** Ancho fijo (CSS). */
  ancho?: string;
  /** Ocultable por el usuario (columna secundaria). */
  secundaria?: boolean;
};

export type PropsTabla<T> = {
  columnas: Columna<T>[];
  filas: T[];
  /** Clave estable por fila. */
  claveFila: (fila: T) => string;
  /** Columnas que el usuario ha ocultado. */
  ocultas?: string[];
  /** Estado vacío (se muestra cuando no hay filas). */
  vacio?: ReactNode;
};

function TablaOpsImpl<T>({
  columnas,
  filas,
  claveFila,
  ocultas = [],
  vacio,
}: PropsTabla<T>) {
  const visibles = columnas.filter((columna) => !ocultas.includes(columna.clave));

  if (filas.length === 0) {
    return <>{vacio ?? null}</>;
  }

  return (
    <div className="max-h-[26rem] overflow-auto">
      <table className="tabla-ops">
        <thead>
          <tr>
            {visibles.map((columna) => (
              <th
                key={columna.clave}
                scope="col"
                style={columna.ancho ? { width: columna.ancho } : undefined}
                className={columna.numerica ? "text-right" : undefined}
              >
                {columna.cabecera}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filas.map((fila) => (
            <tr key={claveFila(fila)}>
              {visibles.map((columna) => (
                <td
                  key={columna.clave}
                  className={columna.numerica ? "num text-right" : undefined}
                >
                  {columna.render(fila)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * `memo` no sirve con genéricos en TypeScript: se exporta la función y la
 * memorización se aplica en la hoja de filas, que es donde está el coste.
 */
export function TablaOps<T>(props: PropsTabla<T>) {
  return <TablaOpsImpl {...props} />;
}

export type PropsFila = {
  children: ReactNode;
};

/** Fila de tabla memorizada (para tablas que se refrescan en bloque). */
export const FilaOps = memo(function FilaOps({ children }: PropsFila) {
  return <>{children}</>;
});
