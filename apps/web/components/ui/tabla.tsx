/**
 * Tabla densa: cabecera pegajosa, líneas de 1px, altura de fila corta y
 * cifras en monoespaciado con cifras tabulares.
 *
 * Genérica y tipada: la consola la usa para los trabajos y el resto de vistas
 * podrán reutilizarla para fuentes, noticias o lotes sin copiar el marcado.
 *
 * Ordenación: las columnas que declaran `ordenable` reciben su cabecera como
 * botón (con `aria-sort` en el `th` y el chevron del estado); el criterio de
 * orden lo aplica la página que usa la tabla —el componente no sabe ordenar
 * datos—, así que la misma pieza sirve para orden en cliente o en servidor.
 */
import { memo, type ReactNode } from "react";
import { IconoOrden } from "./icono";

export type OrdenTabla = { clave: string; dir: "asc" | "desc" };

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
  /** La cabecera ordena por esta columna (requiere `alOrdenar`). */
  ordenable?: boolean;
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
  /** Orden activo; `null` = el orden de llegada (el del servidor). */
  orden?: OrdenTabla | null;
  /** Clic en una cabecera ordenable. */
  alOrdenar?: (clave: string) => void;
};

function TablaOpsImpl<T>({
  columnas,
  filas,
  claveFila,
  ocultas = [],
  vacio,
  orden = null,
  alOrdenar,
}: PropsTabla<T>) {
  const visibles = columnas.filter((columna) => !ocultas.includes(columna.clave));

  if (filas.length === 0) {
    return <>{vacio ?? null}</>;
  }

  return (
    <div className="tabla-contenedor">
      <table className="tabla-ops">
        <thead>
          <tr>
            {visibles.map((columna) => {
              const manda = orden?.clave === columna.clave;
              return (
                <th
                  key={columna.clave}
                  scope="col"
                  style={columna.ancho ? { minWidth: columna.ancho } : undefined}
                  className={columna.numerica ? "text-right" : undefined}
                  aria-sort={manda ? (orden.dir === "asc" ? "ascending" : "descending") : undefined}
                >
                  {columna.ordenable && alOrdenar ? (
                    <button
                      type="button"
                      className="orden-cabecera"
                      onClick={() => alOrdenar(columna.clave)}
                      title={`Ordenar por ${columna.cabecera}`}
                    >
                      {columna.cabecera}
                      <IconoOrden dir={manda ? orden.dir : "asc"} activo={manda} />
                    </button>
                  ) : (
                    columna.cabecera
                  )}
                </th>
              );
            })}
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
