import pandas as pd

UTC_FILE = "data/dataset_habitacion_windows.csv"
COLOMBIA_FILE = "data/dataset_habitacion_windows_colombia_v2.csv"
OUTPUT_FILE = "data/dataset_habitacion_windows_final.csv"


def read_csv_auto(path: str) -> pd.DataFrame:
    """
    Lee CSV detectando si usa ; o , como separador.
    Intenta primero con ; porque sus archivos editados/manuales suelen quedar así.
    """
    # Intento 1: separador ;
    df = pd.read_csv(path, sep=";", decimal=",")
    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]

    # Si quedó una sola columna y parece encabezado pegado, reintentar con coma
    if len(df.columns) == 1 and ("," in df.columns[0] or ";" in df.columns[0]):
        df = pd.read_csv(path, sep=",", decimal=".")
        df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]

    return df


def main():
    print("=== Cargando archivos ===")

    df_utc = read_csv_auto(UTC_FILE)
    df_col = read_csv_auto(COLOMBIA_FILE)

    print("\nColumnas UTC:")
    print(df_utc.columns.tolist())

    print("\nColumnas Colombia:")
    print(df_col.columns.tolist())

    # Validar filas
    if len(df_utc) != len(df_col):
        raise ValueError(
            f"❌ Filas no coinciden: UTC={len(df_utc)} | COL={len(df_col)}"
        )

    # Validar timestamp en UTC
    if "timestamp" not in df_utc.columns:
        raise ValueError(
            f"❌ No se encontró 'timestamp' en UTC. Columnas detectadas: {df_utc.columns.tolist()}"
        )

    # Validar columnas requeridas en Colombia
    required_cols = ["activity", "hora_colombia", "es_noche"]
    for col in required_cols:
        if col not in df_col.columns:
            raise ValueError(
                f"❌ Falta columna '{col}' en dataset Colombia. "
                f"Columnas detectadas: {df_col.columns.tolist()}"
            )

    print("\n=== Copiando columnas ===")
    df_utc["hora_colombia"] = df_col["hora_colombia"]
    df_utc["es_noche"] = df_col["es_noche"]
    df_utc["activity"] = df_col["activity"]

    print("\nVista previa:")
    print(df_utc[["timestamp", "hora_colombia", "es_noche", "activity"]].head().to_string())

    # Guardar TODO el dataset final en formato consistente
    df_utc.to_csv(
        OUTPUT_FILE,
        index=False,
        sep=";",
        decimal="."
    )

    print("\n✅ Dataset final generado correctamente")
    print("Archivo:", OUTPUT_FILE)


if __name__ == "__main__":
    main()