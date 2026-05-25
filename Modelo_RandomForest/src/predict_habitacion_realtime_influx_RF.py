import time
import warnings
import pandas as pd
import joblib

from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.warnings import MissingPivotFunction
from config_influx import INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET

warnings.simplefilter("ignore", MissingPivotFunction)

# =========================
# CONFIGURACIÓN
# =========================
MEASUREMENT = "Sistema_Casa"
ZONE = "Habitacion"

LOOKBACK = "-2m"
WINDOW_SIZE = "5s"
SLEEP_SECONDS = 5

MODEL_FILE = "models/rf_habitacion_recent_3clases.joblib"
ENCODER_FILE = "models/le_habitacion_recent_3clases.joblib"

# Bucket destino de actividades detectadas
ACTIVITY_BUCKET = "activities"
ACTIVITY_TOKEN = "9cJJ_deYH-GyTOqCFokjaliUvU711xozCae8U3WPdb_Dimp_osYeS1UkV1I0AuJu2WRuFLWr2DKLWhu85S4Ccg=="
ACTIVITY_MEASUREMENT = "activity_detection"


def clean_name(text: str) -> str:
    return (
        str(text)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def query_recent_habitacion() -> pd.DataFrame:
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {LOOKBACK})
      |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
      |> filter(fn: (r) => r.zone == "{ZONE}")
      |> keep(columns: ["_time", "_value", "_field", "_measurement", "metric", "node", "sensor", "unit", "zone"])
    '''

    with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        query_api = client.query_api()
        df = query_api.query_data_frame(query=query, org=INFLUX_ORG)

    if isinstance(df, list):
        df = pd.concat(df, ignore_index=True)

    return df


def build_base_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()

    df["zone"] = df["zone"].apply(clean_name)
    df["sensor"] = df["sensor"].apply(clean_name)
    df["metric"] = df["metric"].apply(clean_name)

    df["var"] = df["zone"] + "_" + df["sensor"] + "_" + df["metric"]
    df["timestamp"] = pd.to_datetime(df["_time"], utc=True)

    df_pivot = df.pivot_table(
        index="timestamp",
        columns="var",
        values="_value",
        aggfunc="last"
    )

    df_pivot = df_pivot.sort_index().reset_index()
    return df_pivot


def expand_sleep_state_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    base_col = "habitacion_c1001_habitacion_sleep_state"
    if base_col not in df.columns:
        return df

    s = pd.to_numeric(df[base_col], errors="coerce")

    # Valor consolidado
    df[f"{base_col}_mode_or_default"] = s

    # Codificación real del sensor:
    # 0 = deep
    # 1 = light
    # 2 = awake
    # 3 = no_presence
    df[f"{base_col}_deep"] = (s == 0).astype(float)
    df[f"{base_col}_light"] = (s == 1).astype(float)
    df[f"{base_col}_awake"] = (s == 2).astype(float)
    df[f"{base_col}_no_presence"] = (s == 3).astype(float)

    return df


def build_windows(df_base: pd.DataFrame) -> pd.DataFrame:
    df = df_base.copy()

    if "timestamp" not in df.columns:
        raise ValueError("No se encontró la columna 'timestamp'.")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp")

    df = expand_sleep_state_columns(df)
    df = df.set_index("timestamp")

    # Mantener último valor conocido
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

    df_windows = df.resample(WINDOW_SIZE).agg(agg_dict)
    df_windows.columns = [f"{col}_{stat}" for col, stat in df_windows.columns]
    df_windows = df_windows.dropna(how="all").fillna(0).reset_index()

    return df_windows


def add_time_features(df_windows: pd.DataFrame) -> pd.DataFrame:
    df = df_windows.copy()

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["timestamp_colombia"] = df["timestamp"].dt.tz_convert("America/Bogota")
    df["hora_colombia"] = df["timestamp_colombia"].dt.hour
    df["es_noche"] = df["hora_colombia"].apply(lambda x: 1 if x >= 19 or x <= 7 else 0)

    return df


def adapt_features_to_model(X: pd.DataFrame, model) -> pd.DataFrame:
    expected_features = list(model.named_steps["imputer"].feature_names_in_)

    target_col = "habitacion_c1001_habitacion_sleep_state_mode_or_default"
    min_col = f"{target_col}_min"
    max_col = f"{target_col}_max"

    if target_col not in X.columns:
        if min_col in X.columns and max_col in X.columns:
            X[target_col] = X[max_col]
        elif min_col in X.columns:
            X[target_col] = X[min_col]
        elif max_col in X.columns:
            X[target_col] = X[max_col]

    for col in expected_features:
        if col not in X.columns:
            X[col] = pd.NA

    X = X[expected_features].copy()
    X = X.apply(pd.to_numeric, errors="coerce")

    return X


def apply_final_rule(pred_3class: str, es_noche: int) -> str:
    if pred_3class == "descanso_cama":
        return "dormir" if int(es_noche) == 1 else "siesta"
    return pred_3class


def write_activity_to_influx(last_row, pred_3class: str, pred_final: str):
    timestamp_utc = pd.to_datetime(last_row["timestamp"].iloc[0], utc=True)

    point = (
        Point(ACTIVITY_MEASUREMENT)
        .tag("zone", "habitacion")
        .tag("pred_3class", str(pred_3class))
        .tag("activity", str(pred_final))

        .field("es_noche", int(last_row["es_noche"].iloc[0]))
        .field("hora_colombia", int(last_row["hora_colombia"].iloc[0]))

        .field(
            "tv_current_mean",
            float(last_row.get("habitacion_acs712_habitaciontv_current_mean", pd.Series([0])).iloc[0])
        )
        .field(
            "in_bed_mean",
            float(last_row.get("habitacion_c1001_habitacion_in_bed_mean", pd.Series([0])).iloc[0])
        )
        .field(
            "presence_mean",
            float(last_row.get("habitacion_c1001_habitacion_presence_mean", pd.Series([0])).iloc[0])
        )
        .field(
            "heartbeat_bpm_mean",
            float(last_row.get("habitacion_c1001_habitacion_heartbeat_bpm_mean", pd.Series([0])).iloc[0])
        )
        .field(
            "respiration_rpm_mean",
            float(last_row.get("habitacion_c1001_habitacion_respiration_rpm_mean", pd.Series([0])).iloc[0])
        )
        .field(
            "movement_sum",
            float(last_row.get("habitacion_pir_habitacion_1_movement_sum", pd.Series([0])).iloc[0])
        )

        # Sleep state consolidado
        .field(
            "sleep_state_mode_or_default",
            int(float(last_row.get("habitacion_c1001_habitacion_sleep_state_mode_or_default", pd.Series([0])).iloc[0]))
        )

        # Sleep state derivado
        .field(
            "sleep_state_deep_max",
            float(last_row.get("habitacion_c1001_habitacion_sleep_state_deep_max", pd.Series([0])).iloc[0])
        )
        .field(
            "sleep_state_light_max",
            float(last_row.get("habitacion_c1001_habitacion_sleep_state_light_max", pd.Series([0])).iloc[0])
        )
        .field(
            "sleep_state_awake_max",
            float(last_row.get("habitacion_c1001_habitacion_sleep_state_awake_max", pd.Series([0])).iloc[0])
        )
        .field(
            "sleep_state_no_presence_max",
            float(last_row.get("habitacion_c1001_habitacion_sleep_state_no_presence_max", pd.Series([0])).iloc[0])
        )

        .time(timestamp_utc)
    )

    with InfluxDBClient(
        url=INFLUX_URL,
        token=ACTIVITY_TOKEN,
        org=INFLUX_ORG
    ) as client:
        write_api = client.write_api(write_options=WriteOptions(batch_size=1, flush_interval=1000))
        write_api.write(bucket=ACTIVITY_BUCKET, org=INFLUX_ORG, record=point)


def predict_once(model, le):
    df_raw = query_recent_habitacion()

    if df_raw.empty:
        print("⚠ No se encontraron datos recientes de Habitación.")
        return

    df_base = build_base_dataframe(df_raw)
    if df_base.empty:
        print("⚠ No se pudo construir el dataset base.")
        return

    df_windows = build_windows(df_base)
    if df_windows.empty:
        print("⚠ No se pudieron construir ventanas.")
        return

    df_windows = add_time_features(df_windows)

    # Tomar la ventana más reciente
    last_row = df_windows.iloc[[-1]].copy()

    X = last_row.drop(
        columns=[
            "timestamp",
            "timestamp_colombia"
        ],
        errors="ignore"
    ).copy()

    X = adapt_features_to_model(X, model)

    y_pred_encoded = model.predict(X)
    pred_3class = le.inverse_transform(y_pred_encoded)[0]
    pred_final = apply_final_rule(pred_3class, int(last_row["es_noche"].iloc[0]))

    # Mostrar sleep_state en consola
    print("sleep_state_mode_or_default:",
          last_row.get("habitacion_c1001_habitacion_sleep_state_mode_or_default", pd.Series([None])).iloc[0])

    # Guardar en Influx
    write_activity_to_influx(last_row, pred_3class, pred_final)

    timestamp_utc = str(last_row["timestamp"].iloc[0])
    timestamp_col = str(last_row["timestamp_colombia"].iloc[0])
    hora_col = int(last_row["hora_colombia"].iloc[0])
    es_noche = int(last_row["es_noche"].iloc[0])

    print("\n========================================")
    print("VENTANA UTC:      ", timestamp_utc)
    print("VENTANA COLOMBIA: ", timestamp_col)
    print("HORA COLOMBIA:    ", hora_col)
    print("ES NOCHE:         ", es_noche)
    print("PRED 3 CLASES:    ", pred_3class)
    print("PRED FINAL:       ", pred_final)

    inspect_cols = [
        "habitacion_acs712_habitaciontv_current_mean",
        "habitacion_c1001_habitacion_in_bed_mean",
        "habitacion_c1001_habitacion_presence_mean",
        "habitacion_c1001_habitacion_heartbeat_bpm_mean",
        "habitacion_c1001_habitacion_respiration_rpm_mean",
        "habitacion_pir_habitacion_1_movement_sum",
        "habitacion_c1001_habitacion_sleep_state_mode_or_default",
    ]

    print("\nVariables clave:")
    for col in inspect_cols:
        if col in last_row.columns:
            print(f"{col}: {last_row[col].iloc[0]}")
    print("========================================")


def main():
    print("=== Cargando modelo ===")
    model = joblib.load(MODEL_FILE)
    le = joblib.load(ENCODER_FILE)

    print("=== Iniciando inferencia en tiempo real ===")
    print(f"Consulta cada {SLEEP_SECONDS} segundos")
    print(f"Lookback: {LOOKBACK}")
    print(f"Ventana: {WINDOW_SIZE}")

    while True:
        try:
            predict_once(model, le)
        except KeyboardInterrupt:
            print("\n⏹ Proceso detenido por el usuario.")
            break
        except Exception as e:
            print(f"\n❌ Error en inferencia: {e}")

        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()