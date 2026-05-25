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
ZONE = "Banio"

LOOKBACK = "-2m"
WINDOW_SIZE = "30s"
SLEEP_SECONDS = 2

MODEL_FILE = "models/rf_banio.joblib"
ENCODER_FILE = "models/le_banio.joblib"

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


def query_recent_banio() -> pd.DataFrame:
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


def build_windows(df_base: pd.DataFrame) -> pd.DataFrame:
    df = df_base.copy()

    if "timestamp" not in df.columns:
        raise ValueError("No se encontró la columna 'timestamp'.")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    for col in df.columns:
        if col != "timestamp":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values("timestamp").set_index("timestamp")

    # Igual que en build_windows_banio.py
    df = df.ffill()

    agg_dict = {}

    for col in df.columns:
        c = col.lower()

        if any(x in c for x in ["temperature", "humidity", "distance"]):
            agg_dict[col] = ["mean", "min", "max", "std"]

        elif any(x in c for x in ["movement", "flow_state"]):
            agg_dict[col] = ["mean", "sum", "max"]

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

    for col in expected_features:
        if col not in X.columns:
            X[col] = pd.NA

    X = X[expected_features].copy()
    X = X.apply(pd.to_numeric, errors="coerce")

    return X


def write_activity_to_influx(last_row, pred_label: str):
    timestamp_utc = pd.to_datetime(last_row["timestamp"].iloc[0], utc=True)

    point = (
        Point(ACTIVITY_MEASUREMENT)
        .tag("zone", "banio")
        .tag("activity", str(pred_label))

        .field("es_noche", int(last_row["es_noche"].iloc[0]))
        .field("hora_colombia", int(last_row["hora_colombia"].iloc[0]))

        .field(
            "banio_distance_mean",
            float(last_row.get("banio_hc_sr04_banio_distance_mean", pd.Series([0])).iloc[0])
        )
        .field(
            "ducha_distance_mean",
            float(last_row.get("banio_hc_sr04_ducha_distance_mean", pd.Series([0])).iloc[0])
        )
        .field(
            "ducha1_distance_mean",
            float(last_row.get("banio_hc_sr04_ducha1_distance_mean", pd.Series([0])).iloc[0])
        )
        .field(
            "pir_banio_sum",
            float(last_row.get("banio_pir_banio_1_movement_sum", pd.Series([0])).iloc[0])
        )
        .field(
            "pir_ducha_sum",
            float(last_row.get("banio_pir_ducha_movement_sum", pd.Series([0])).iloc[0])
        )
        .field(
            "flow_banio_sum",
            float(last_row.get("banio_yf_s201_a_banio_flow_state_sum", pd.Series([0])).iloc[0])
        )
        .field(
            "flow_ducha_sum",
            float(last_row.get("banio_yf_s201_ducha_flow_state_sum", pd.Series([0])).iloc[0])
        )
        .field(
            "flow_lavamanos_sum",
            float(last_row.get("banio_yf_s201_lavamanos_flow_state_sum", pd.Series([0])).iloc[0])
        )
        .field(
            "temperature_mean",
            float(last_row.get("banio_dht11_ducha_temperature_mean", pd.Series([0])).iloc[0])
        )
        .field(
            "humidity_mean",
            float(last_row.get("banio_dht11_ducha_humidity_mean", pd.Series([0])).iloc[0])
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
    df_raw = query_recent_banio()

    if df_raw.empty:
        print("⚠ No se encontraron datos recientes de Baño.")
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
    pred_label = le.inverse_transform(y_pred_encoded)[0]

    write_activity_to_influx(last_row, pred_label)

    timestamp_utc = str(last_row["timestamp"].iloc[0])
    timestamp_col = str(last_row["timestamp_colombia"].iloc[0])
    hora_col = int(last_row["hora_colombia"].iloc[0])
    es_noche = int(last_row["es_noche"].iloc[0])

    print("\n========================================")
    print("VENTANA UTC:      ", timestamp_utc)
    print("VENTANA COLOMBIA: ", timestamp_col)
    print("HORA COLOMBIA:    ", hora_col)
    print("ES NOCHE:         ", es_noche)
    print("PREDICCIÓN:       ", pred_label)

    inspect_cols = [
        "banio_hc_sr04_banio_distance_mean",
        "banio_hc_sr04_ducha_distance_mean",
        "banio_hc_sr04_ducha1_distance_mean",
        "banio_pir_banio_1_movement_sum",
        "banio_pir_ducha_movement_sum",
        "banio_yf_s201_a_banio_flow_state_sum",
        "banio_yf_s201_ducha_flow_state_sum",
        "banio_yf_s201_lavamanos_flow_state_sum",
        "banio_dht11_ducha_temperature_mean",
        "banio_dht11_ducha_humidity_mean",
    ]

    print("\nVariables clave:")
    for col in inspect_cols:
        if col in last_row.columns:
            print(f"{col}: {last_row[col].iloc[0]}")
    print("========================================")


def main():
    print("=== Cargando modelo de baño ===")
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