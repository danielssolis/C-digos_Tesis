import pandas as pd
from influxdb_client import InfluxDBClient

from config_influx import INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET


# =========================
# CONFIGURACIÓN
# =========================
MEASUREMENT = "Sistema_Casa"
ZONE = "Habitacion"

# Cambie este rango cuando quiera
RANGE_START = "-3d"

# Archivos de salida
RAW_OUTPUT_FILE = "data/dataset_habitacion_recent_raw.csv"
WINDOWS_OUTPUT_FILE = "data/dataset_habitacion_recent_windows_colombia.csv"


def clean_name(text: str) -> str:
    return (
        str(text)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def query_influx() -> pd.DataFrame:
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {RANGE_START})
      |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
      |> filter(fn: (r) => r.zone == "{ZONE}")
      |> keep(columns: ["_time", "_value", "_field", "_measurement", "metric", "node", "sensor", "unit", "zone"])
    '''

    with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        query_api = client.query_api()
        df = query_api.query_data_frame(query=query, org=INFLUX_ORG)

    if isinstance(df, list):
        df = pd.concat(df, ignore_index=True)

    if df.empty:
        raise ValueError("La consulta no devolvió datos para Habitación.")

    return df


def build_long_dataset(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Normalizar nombres
    df["zone"] = df["zone"].apply(clean_name)
    df["sensor"] = df["sensor"].apply(clean_name)
    df["metric"] = df["metric"].apply(clean_name)

    # Nombre de variable
    df["var"] = df["zone"] + "_" + df["sensor"] + "_" + df["metric"]

    # Timestamp
    df["timestamp"] = pd.to_datetime(df["_time"], utc=True)

    # Guardar una versión cruda útil para auditoría
    df.to_csv(RAW_OUTPUT_FILE, index=False)

    # Pivot
    df_pivot = df.pivot_table(
        index="timestamp",
        columns="var",
        values="_value",
        aggfunc="last"
    )

    df_pivot = df_pivot.sort_index().reset_index()

    return df_pivot


def expand_sleep_state_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crea columnas auxiliares derivadas de sleep_state si existe.
    Ajuste estos códigos si en su sensor cambia el significado.
    """
    df = df.copy()

    base_col = "habitacion_c1001_habitacion_sleep_state"
    if base_col not in df.columns:
        return df

    # Convertir a numérico
    s = pd.to_numeric(df[base_col], errors="coerce")

    # Mantener valor base
    df[f"{base_col}_mode_or_default"] = s

    # One-hot simples por estado
    # Ajuste si su codificación cambia:
    # 0 = no_presence
    # 1 = awake
    # 2 = light
    # 3 = deep
    df[f"{base_col}_no_presence"] = (s == 0).astype(float)
    df[f"{base_col}_awake"] = (s == 1).astype(float)
    df[f"{base_col}_light"] = (s == 2).astype(float)
    df[f"{base_col}_deep"] = (s == 3).astype(float)

    return df


def build_windows(df: pd.DataFrame, window_size: str = "30s") -> pd.DataFrame:
    df = df.copy()

    if "timestamp" not in df.columns:
        raise ValueError("No se encontró la columna 'timestamp'.")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp")

    # Expandir sleep_state antes de agrupar
    df = expand_sleep_state_columns(df)

    df = df.set_index("timestamp")

    # Forward fill para mantener el último valor conocido
    df = df.ffill()

    agg_dict = {}

    for col in df.columns:
        c = col.lower()

        if any(x in c for x in ["heartbeat", "respiration", "current", "temperature", "humidity", "distance", "sleep_quality"]):
            agg_dict[col] = ["mean", "min", "max", "std"]

        elif any(x in c for x in [
            "movement",
            "presence",
            "in_bed",
            "flow_state",
            "apnea_events",
            "turnover_count",
            "large_body_move",
            "minor_body_move",
            "_deep",
            "_light",
            "_awake",
            "_no_presence"
        ]):
            agg_dict[col] = ["mean", "sum", "max"]

        elif "sleep_state" in c:
            agg_dict[col] = ["min", "max"]
        else:
            agg_dict[col] = ["mean", "max"]

    df_windows = df.resample(window_size).agg(agg_dict)
    df_windows.columns = [f"{col}_{stat}" for col, stat in df_windows.columns]
    df_windows = df_windows.dropna(how="all").fillna(0).reset_index()

    return df_windows


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["timestamp_colombia"] = df["timestamp"].dt.tz_convert("America/Bogota")
    df["hora_colombia"] = df["timestamp_colombia"].dt.hour
    df["es_noche"] = df["hora_colombia"].apply(lambda x: 1 if x >= 19 or x <= 7 else 0)

    return df


def main():
    print("=== Consultando datos recientes de Habitación en InfluxDB ===")
    df_raw = query_influx()

    print("Datos crudos:", df_raw.shape)
    print("Primeras filas:")
    print(df_raw.head().to_string())

    print("\n=== Construyendo dataset base ===")
    df_base = build_long_dataset(df_raw)
    print("Dataset base:", df_base.shape)

    print("\n=== Construyendo ventanas ===")
    df_windows = build_windows(df_base, window_size="30s")
    print("Dataset por ventanas:", df_windows.shape)

    print("\n=== Agregando hora Colombia y es_noche ===")
    df_windows = add_time_features(df_windows)

    # Guardar final en formato consistente
    df_windows.to_csv(WINDOWS_OUTPUT_FILE, index=False, sep=";", decimal=".")

    print("\n✅ Dataset reciente de Habitación generado correctamente")
    print("Archivo crudo:", RAW_OUTPUT_FILE)
    print("Archivo por ventanas:", WINDOWS_OUTPUT_FILE)

    print("\nPrimeras filas del dataset final:")
    preview_cols = [c for c in ["timestamp", "timestamp_colombia", "hora_colombia", "es_noche"] if c in df_windows.columns]
    print(df_windows[preview_cols].head().to_string())


if __name__ == "__main__":
    main()