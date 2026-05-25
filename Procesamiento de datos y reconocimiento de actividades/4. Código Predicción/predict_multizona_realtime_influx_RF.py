import time
import warnings
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple, Set, Union

import pandas as pd
import joblib

from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.warnings import MissingPivotFunction
from config_influx import INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET

warnings.simplefilter("ignore", MissingPivotFunction)

# =========================================================
# CONFIG GENERAL
# =========================================================
MEASUREMENT = "Sistema_Casa"
PIR_LOOKBACK = "-20s"
POLL_SECONDS = 5

LOOKBACK_BY_ZONE = {
    "habitacion": "-2m",
    "banio": "-2m",
    "sala": "-2m",
    "cocina_comedor": "-2m",
}

WINDOW_SIZE_BY_ZONE = {
    "habitacion": "30s",
    "banio": "30s",
    "sala": "30s",
    "cocina_comedor": "30s",
}

ZONE_COOLDOWN_SECONDS = {
    "habitacion": 5,
    "banio": 5,
    "sala": 5,
    "cocina_comedor": 5,
}

MAX_INACTIVE_STREAK = 3

# Regla global caminar_casa
WALKING_WINDOW_SECONDS = 120
MIN_ZONES_FOR_WALKING = 3

# Regla consumo_alimentos
COOKING_MEMORY_SECONDS = 45 * 60
COMEDOR_STABLE_STREAK_REQUIRED = 2

ACTIVITY_BUCKET = "activitiesrf"
ACTIVITY_TOKEN = "kIT2XNAgy0phmC8zVbSg4VUqkxY191UwroE7R_CG9Keoe0L5TjPohI6JUt-B3L9u2VoW2b75WHNOqp9drUOYUA=="
ACTIVITY_MEASUREMENT = "activity_detection"


# =========================================================
# CONFIG POR ZONA
# =========================================================
@dataclass
class ZoneConfig:
    zone_tag_influx: Union[str, List[str]]
    model_file: str
    encoder_file: str
    pir_vars: List[str]
    inspect_cols: List[str]
    use_sleep_expansion: bool
    inactive_labels: Set[str]


ZONE_CONFIG: Dict[str, ZoneConfig] = {
    "habitacion": ZoneConfig(
        zone_tag_influx="Habitacion",
        model_file="models/rf_habitacion.joblib",
        encoder_file="models/le_habitacion.joblib",
        pir_vars=[
            "habitacion_pir_habitacion_1_movement",
        ],
        inspect_cols=[
            "habitacion_acs712_habitaciontv_current_mean",
            "habitacion_acs712_habitaciontv_current_last",
            "habitacion_acs712_habitaciontv_current_max",
            "habitacion_c1001_habitacion_in_bed_mean",
            "habitacion_c1001_habitacion_presence_mean",
            "habitacion_c1001_habitacion_heartbeat_bpm_mean",
            "habitacion_c1001_habitacion_respiration_rpm_mean",
            "habitacion_pir_habitacion_1_movement_sum",
            "habitacion_c1001_habitacion_sleep_state_min",
            "habitacion_c1001_habitacion_sleep_state_max",
            "habitacion_c1001_habitacion_sleep_state_mode_or_default_min",
            "habitacion_c1001_habitacion_sleep_state_mode_or_default_max",
        ],
        use_sleep_expansion=True,
        inactive_labels={
            "sin_act_hab",
            "sin_act_habitacion",
            "sin_actividad_habitacion",
            "sin_actividad",
            "no_activity",
        },
    ),

    "banio": ZoneConfig(
        zone_tag_influx="Banio",
        model_file="models/rf_banio.joblib",
        encoder_file="models/le_banio.joblib",
        pir_vars=[
            "banio_pir_banio_1_movement",
            "banio_pir_ducha_movement",
        ],
        inspect_cols=[
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
        ],
        use_sleep_expansion=False,
        inactive_labels={
            "sin_act_banio",
            "sin_actividad_banio",
            "sin_actividad",
            "no_activity",
        },
    ),

    "sala": ZoneConfig(
        zone_tag_influx="Sala",
        model_file="models/rf_sala.joblib",
        encoder_file="models/le_sala.joblib",
        pir_vars=[
            "sala_pir_sala_1_movement",
        ],
        inspect_cols=[
            "sala_acs712_salatv_current_last",
            "sala_acs712_salatv_current_max",
            "sala_hc_sr04_sala_distance_last",
            "sala_hc_sr04_sala_distance_min",
            "sala_hc_sr04_salatv_distance_last",
            "sala_hc_sr04_salatv_distance_min",
            "sala_c1001_sala_presence_last",
            "sala_c1001_sala_in_bed_last",
            "sala_c1001_sala_sleep_state_last",
            "sala_pir_sala_1_movement_last",
            "sala_pir_sala_1_movement_sum",
        ],
        use_sleep_expansion=False,
        inactive_labels={
            "sin_act_sala",
            "sin_actividad_sala",
            "sin_actividad",
            "no_activity",
        },
    ),

    "cocina_comedor": ZoneConfig(
        zone_tag_influx=["Cocina", "Comedor"],
        model_file="models/rf_cocina_comedor.joblib",
        encoder_file="models/le_cocina_comedor.joblib",
        pir_vars=[
            "cocina_pir_cocina_movement",
            "cocina_pir_cocina_1_movement",
            "comedor_pir_comedor_movement",
            "comedor_pir_comedor_1_movement",
        ],
        inspect_cols=[
            "cocina_pir_cocina_movement_last",
            "cocina_pir_cocina_movement_sum",
            "comedor_pir_comedor_movement_last",
            "comedor_pir_comedor_movement_sum",
            "cocina_yf_s201_cocina_flow_state_last",
            "cocina_yf_s201_cocina_flow_state_sum",
            "cocina_dht11_cocina_temperature_mean",
            "cocina_dht11_cocina_humidity_mean",
            "cocina_hc_sr04_cocina_distance_last",
            "cocina_hc_sr04_cocina_distance_min",
            "cocina_hc_sr04_cocina_distance_max",
        ],
        use_sleep_expansion=False,
        inactive_labels={
            "sin_act_cocina_comedor",
            "sin_actividad_cocina_comedor",
            "sin_actividad",
            "no_activity",
        },
    ),
}


# =========================================================
# HELPERS
# =========================================================
def clean_name(text: str) -> str:
    return (
        str(text)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def get_query_df(query: str) -> pd.DataFrame:
    with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        query_api = client.query_api()
        df = query_api.query_data_frame(query=query, org=INFLUX_ORG)

    if isinstance(df, list):
        if len(df) == 0:
            return pd.DataFrame()
        df = pd.concat(df, ignore_index=True)

    return df


def build_zone_filter(zone_tag_influx: Union[str, List[str]]) -> str:
    if isinstance(zone_tag_influx, str):
        return f'r.zone == "{zone_tag_influx}"'

    return " or ".join([f'r.zone == "{z}"' for z in zone_tag_influx])


def get_value_safe(last_row: pd.DataFrame, col: str, default: float = 0.0) -> float:
    if col not in last_row.columns:
        return default

    value = pd.to_numeric(last_row[col].iloc[0], errors="coerce")
    if pd.isna(value):
        return default

    return float(value)


# =========================================================
# 1) PIR: DETECTAR SI OTRA ZONA TOMA EL CONTROL
# =========================================================
def query_recent_pirs() -> pd.DataFrame:
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {PIR_LOOKBACK})
      |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
      |> filter(fn: (r) => r.metric == "movement")
      |> filter(fn: (r) => r.zone == "Habitacion" or r.zone == "Banio" or r.zone == "Sala" or r.zone == "Cocina" or r.zone == "Comedor")
      |> keep(columns: ["_time", "_value", "zone", "sensor", "metric"])
    '''
    return get_query_df(query)


def get_latest_pir_activation() -> Optional[Tuple[str, pd.Timestamp, str]]:
    df = query_recent_pirs()

    if df.empty:
        print("DEBUG PIR: no llegaron PIR recientes")
        return None

    df = df.copy()
    df["zone"] = df["zone"].apply(clean_name)
    df["sensor"] = df["sensor"].apply(clean_name)
    df["metric"] = df["metric"].apply(clean_name)
    df["timestamp"] = pd.to_datetime(df["_time"], utc=True)
    df["_value"] = pd.to_numeric(df["_value"], errors="coerce").fillna(0)

    df["var"] = df["zone"] + "_" + df["sensor"] + "_" + df["metric"]

    #print("\n===== DEBUG PIR RECIENTES =====")
    #print(df[["timestamp", "zone", "sensor", "metric", "_value", "var"]]
          #.sort_values("timestamp", ascending=False)
          #.head(20)
          #.to_string(index=False))

    active = df[df["_value"] >= 1].copy()
    if active.empty:
        print("DEBUG PIR: llegaron PIR, pero ninguno activo con valor >= 1")
        return None

    active = active.sort_values("timestamp", ascending=False).reset_index(drop=True)

    #print("\n===== DEBUG PIR ACTIVOS =====")
    #print(active[["timestamp", "zone", "sensor", "metric", "_value", "var"]]
          #.head(20)
          #.to_string(index=False))

    for _, row in active.iterrows():
        var = row["var"]
        ts = row["timestamp"]

        for zone_name, cfg in ZONE_CONFIG.items():
            if var in cfg.pir_vars:
                print(f"✅ PIR reconocido: {var} -> zona {zone_name}")
                return (zone_name, ts, var)

        print(f"⚠ PIR activo no mapeado en ZONE_CONFIG.pir_vars: {var}")

    return None


# =========================================================
# 2) EXTRACCIÓN BASE
# =========================================================
def query_recent_zone(zone_name: str) -> pd.DataFrame:
    cfg = ZONE_CONFIG[zone_name]
    zone_filter = build_zone_filter(cfg.zone_tag_influx)

    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {LOOKBACK_BY_ZONE[zone_name]})
      |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
      |> filter(fn: (r) => {zone_filter})
      |> keep(columns: ["_time", "_value", "_field", "_measurement", "metric", "node", "sensor", "unit", "zone"])
    '''
    return get_query_df(query)


def build_base_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    if df_raw.empty:
        return pd.DataFrame()

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

    return df_pivot.sort_index().reset_index()


# =========================================================
# 3) FEATURES HABITACIÓN
# =========================================================
def expand_sleep_state_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    base_col = "habitacion_c1001_habitacion_sleep_state"
    if base_col not in df.columns:
        return df

    s = pd.to_numeric(df[base_col], errors="coerce")

    df[f"{base_col}_mode_or_default"] = s
    df[f"{base_col}_deep"] = (s == 0).astype(float)
    df[f"{base_col}_light"] = (s == 1).astype(float)
    df[f"{base_col}_awake"] = (s == 2).astype(float)
    df[f"{base_col}_no_presence"] = (s == 3).astype(float)

    return df


# =========================================================
# 4) VENTANAS POR ZONA
# =========================================================
def build_windows_for_zone(df_base: pd.DataFrame, zone_name: str) -> pd.DataFrame:
    if df_base.empty:
        return pd.DataFrame()

    df = df_base.copy()

    if "timestamp" not in df.columns:
        raise ValueError("No se encontró la columna 'timestamp'.")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    for col in df.columns:
        if col != "timestamp":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values("timestamp")

    if ZONE_CONFIG[zone_name].use_sleep_expansion:
        df = expand_sleep_state_columns(df)

    # =====================================================
    # PREPROCESADO ESPECÍFICO POR ZONA
    # =====================================================
    if zone_name in {"sala", "cocina_comedor"}:
        for col in df.columns:
            if "distance" in col.lower():
                df[col] = df[col].mask(df[col] <= 0)
                df[col] = df[col].mask(df[col] > 400)

    df = df.set_index("timestamp")

    # =====================================================
    # FILL POR ZONA
    # =====================================================
    if zone_name == "habitacion" or zone_name == "banio":
        df = df.ffill()

    elif zone_name in {"sala", "cocina_comedor"}:
        for col in df.columns:
            c = col.lower()
            if "distance" in c or "movement" in c:
                continue
            df[col] = df[col].ffill()

    # =====================================================
    # AGREGACIONES
    # =====================================================
    agg_dict = {}

    for col in df.columns:
        c = col.lower()

        if zone_name == "habitacion":
            # IMPORTANTE: debe coincidir con el dataset nuevo de habitación.
            # El ACS712/current incluye last porque el modelo nuevo fue entrenado con
            # habitacion_acs712_habitaciontv_current_last.
            if "current" in c or "acs712" in c:
                agg_dict[col] = ["mean", "min", "max", "std", "last"]
            elif any(x in c for x in ["heartbeat", "respiration", "temperature", "humidity", "distance", "sleep_quality"]):
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

        elif zone_name == "banio":
            if any(x in c for x in ["temperature", "humidity", "distance"]):
                agg_dict[col] = ["mean", "min", "max", "std"]
            elif any(x in c for x in ["movement", "flow_state"]):
                agg_dict[col] = ["mean", "sum", "max"]
            else:
                agg_dict[col] = ["mean", "max"]

        elif zone_name == "sala":
            if any(x in c for x in ["heartbeat", "respiration", "temperature", "humidity"]):
                agg_dict[col] = ["mean", "min", "max", "std"]
            elif "distance" in c:
                agg_dict[col] = ["last", "min", "max"]
            elif "current" in c:
                agg_dict[col] = ["last", "max"]
            elif any(x in c for x in ["presence", "in_bed", "sleep_state"]):
                agg_dict[col] = ["last"]
            elif "movement" in c:
                agg_dict[col] = ["last", "sum", "max"]
            elif any(x in c for x in ["turnover", "body_move", "apnea"]):
                agg_dict[col] = ["sum", "max"]
            else:
                agg_dict[col] = ["last"]

        elif zone_name == "cocina_comedor":
            if any(x in c for x in ["temperature", "humidity"]):
                agg_dict[col] = ["mean", "min", "max", "std"]
            elif "distance" in c:
                agg_dict[col] = ["last", "min", "max"]
            elif "current" in c:
                agg_dict[col] = ["last", "max"]
            elif "movement" in c:
                agg_dict[col] = ["last", "sum", "max"]
            elif "flow_state" in c:
                agg_dict[col] = ["last", "sum", "max"]
            else:
                agg_dict[col] = ["last"]

    df_windows = df.resample(WINDOW_SIZE_BY_ZONE[zone_name]).agg(agg_dict)
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


# =========================================================
# 5) ADAPTACIÓN AL MODELO
# =========================================================
def adapt_features_to_model(X: pd.DataFrame, model, zone_name: str) -> pd.DataFrame:
    expected_features = list(model.named_steps["imputer"].feature_names_in_)

    if zone_name == "habitacion":
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


# =========================================================
# 6) POSTPROCESO
# =========================================================
def apply_final_rule(zone_name: str, pred_base: str, es_noche: int) -> str:
    if zone_name == "habitacion" and pred_base == "descanso_cama":
        return "dormir" if int(es_noche) == 1 else "siesta"

    if zone_name == "sala" and pred_base == "descanso_sala":
        return "dormir" if int(es_noche) == 1 else "siesta"

    return pred_base


def is_inactive_prediction(zone_name: str, pred_label: str) -> bool:
    return clean_name(pred_label) in ZONE_CONFIG[zone_name].inactive_labels


def comedor_pir_active(last_row: pd.DataFrame) -> bool:
    cols = [
        "comedor_pir_comedor_movement_last",
        "comedor_pir_comedor_movement_sum",
        "comedor_pir_comedor_movement_max",
    ]

    for col in cols:
        if get_value_safe(last_row, col, 0) >= 1:
            return True

    return False


def apply_food_consumption_rule(
    pred_base: str,
    pred_final: str,
    last_row: pd.DataFrame,
    last_cooking_ts: Optional[float],
    comedor_stable_streak: int,
) -> Tuple[str, Optional[float], int]:
    now = time.time()

    if clean_name(pred_base) == "cocinando":
        last_cooking_ts = now
        comedor_stable_streak = 0
        return pred_final, last_cooking_ts, comedor_stable_streak

    cooking_recent = (
        last_cooking_ts is not None
        and (now - last_cooking_ts) <= COOKING_MEMORY_SECONDS
    )

    if cooking_recent and comedor_pir_active(last_row):
        comedor_stable_streak += 1
    else:
        comedor_stable_streak = 0

    if cooking_recent and comedor_stable_streak >= COMEDOR_STABLE_STREAK_REQUIRED:
        return "consumo_alimentos", last_cooking_ts, comedor_stable_streak

    return pred_final, last_cooking_ts, comedor_stable_streak


def update_walking_rule(
    walking_events: List[Dict[str, object]],
    zone_name: str,
    pred_final: str,
) -> Tuple[str, List[Dict[str, object]]]:
    now = time.time()

    if is_inactive_prediction(zone_name, pred_final):
        walking_events.append({
            "zone": zone_name,
            "time": now,
        })

    walking_events = [
        event for event in walking_events
        if now - float(event["time"]) <= WALKING_WINDOW_SECONDS
    ]

    recent_zones = set(str(event["zone"]) for event in walking_events)

    if len(recent_zones) >= MIN_ZONES_FOR_WALKING:
        walking_events.clear()
        return "caminar_casa", walking_events

    return pred_final, walking_events


# =========================================================
# 7) ESCRITURA EN INFLUX
# SOLO ACTIVIDAD + HORA/TIMESTAMP
# =========================================================
def write_activity_to_influx(last_row: pd.DataFrame, zone_name: str, pred_base: str, pred_final: str):
    timestamp_utc = pd.to_datetime(last_row["timestamp"].iloc[0], utc=True)
    timestamp_col = pd.to_datetime(last_row["timestamp_colombia"].iloc[0])

    point = (
        Point(ACTIVITY_MEASUREMENT)
        .tag("zone", zone_name)
        .tag("pred_base", str(pred_base))
        .tag("activity", str(pred_final))
        .field("hora_colombia", int(last_row["hora_colombia"].iloc[0]))
        .field("timestamp_colombia_text", str(timestamp_col))
        .time(timestamp_utc)
    )

    with InfluxDBClient(url=INFLUX_URL, token=ACTIVITY_TOKEN, org=INFLUX_ORG) as client:
        write_api = client.write_api(write_options=WriteOptions(batch_size=1, flush_interval=1000))
        write_api.write(bucket=ACTIVITY_BUCKET, org=INFLUX_ORG, record=point)


# =========================================================
# 8) INFERENCIA
# =========================================================
def predict_once_for_zone(zone_name: str, model, le) -> Tuple[str, str, pd.DataFrame]:
    df_raw = query_recent_zone(zone_name)

    if df_raw.empty:
        raise ValueError(f"No se encontraron datos recientes de {zone_name}.")

    df_base = build_base_dataframe(df_raw)
    if df_base.empty:
        raise ValueError(f"No se pudo construir dataset base de {zone_name}.")

    df_windows = build_windows_for_zone(df_base, zone_name)
    if df_windows.empty:
        raise ValueError(f"No se pudieron construir ventanas de {zone_name}.")

    df_windows = add_time_features(df_windows)
    last_row = df_windows.iloc[[-1]].copy()

    X = last_row.drop(columns=["timestamp", "timestamp_colombia"], errors="ignore").copy()
    X = adapt_features_to_model(X, model, zone_name)

    y_pred_encoded = model.predict(X)
    pred_base = le.inverse_transform(y_pred_encoded)[0]
    pred_final = apply_final_rule(zone_name, pred_base, int(last_row["es_noche"].iloc[0]))

    return pred_base, pred_final, last_row


def print_terminal_log(zone_name: str, pred_base: str, pred_final: str, last_row: pd.DataFrame):
    print("\n========================================")
    print("ZONA ACTIVA:       ", zone_name)
    print("VENTANA UTC:       ", str(last_row["timestamp"].iloc[0]))
    print("VENTANA COLOMBIA:  ", str(last_row["timestamp_colombia"].iloc[0]))
    print("HORA COLOMBIA:     ", int(last_row["hora_colombia"].iloc[0]))
    print("PRED BASE:         ", pred_base)
    print("PRED FINAL:        ", pred_final)
    print("Variables clave:")
    for col in ZONE_CONFIG[zone_name].inspect_cols:
        if col in last_row.columns:
            print(f"{col}: {last_row[col].iloc[0]}")
    print("========================================")


# =========================================================
# 9) MAIN
# =========================================================
def main():
    print("=== Cargando modelos ===")
    models = {}
    encoders = {}

    for zone_name, cfg in ZONE_CONFIG.items():
        print(f"Cargando {zone_name}: {cfg.model_file} / {cfg.encoder_file}")
        models[zone_name] = joblib.load(cfg.model_file)
        encoders[zone_name] = joblib.load(cfg.encoder_file)

    print("=== Iniciando despachador por PIR + persistencia por actividad ===")

    active_zone: Optional[str] = None
    active_event_ts: Optional[pd.Timestamp] = None

    last_run_at = {
        "habitacion": 0.0,
        "banio": 0.0,
        "sala": 0.0,
        "cocina_comedor": 0.0,
    }

    inactive_streak = {
        "habitacion": 0,
        "banio": 0,
        "sala": 0,
        "cocina_comedor": 0,
    }

    walking_events: List[Dict[str, object]] = []

    last_cooking_ts: Optional[float] = None
    comedor_stable_streak = 0

    while True:
        try:
            latest = get_latest_pir_activation()

            # Si hay PIR nuevo, la nueva zona toma el control inmediatamente
            if latest is not None:
                new_zone, new_event_ts, trigger_var = latest

                if (
                    active_zone is None
                    or active_event_ts is None
                    or new_event_ts > active_event_ts
                    or new_zone != active_zone
                ):
                    old_zone = active_zone
                    active_zone = new_zone
                    active_event_ts = new_event_ts
                    inactive_streak[new_zone] = 0
                    print(f"🔁 Cambio de zona activa: {old_zone} -> {active_zone} por {trigger_var}")

            if active_zone is None:
                print("… todavía no hay zona activa.")
                time.sleep(POLL_SECONDS)
                continue

            now_ts = time.time()
            cooldown = ZONE_COOLDOWN_SECONDS[active_zone]

            if now_ts - last_run_at[active_zone] < cooldown:
                print(f"⏳ {active_zone} en cooldown, esperando...")
                time.sleep(POLL_SECONDS)
                continue

            print(f"🟢 Ejecutando reconocimiento con modelo de {active_zone}")

            pred_base, pred_final, last_row = predict_once_for_zone(
                active_zone,
                models[active_zone],
                encoders[active_zone]
            )

            # Regla consumo_alimentos
            if active_zone == "cocina_comedor":
                pred_final, last_cooking_ts, comedor_stable_streak = apply_food_consumption_rule(
                    pred_base=pred_base,
                    pred_final=pred_final,
                    last_row=last_row,
                    last_cooking_ts=last_cooking_ts,
                    comedor_stable_streak=comedor_stable_streak,
                )

                print(
                    f"🍽 consumo_alimentos | "
                    f"last_cooking_ts={last_cooking_ts} | "
                    f"comedor_stable_streak={comedor_stable_streak}"
                )

            # Regla caminar_casa
            pred_final, walking_events = update_walking_rule(
                walking_events=walking_events,
                zone_name=active_zone,
                pred_final=pred_final,
            )

            print(f"🚶 caminar_casa | eventos_recientes={walking_events}")

            # Log en terminal con variables
            print_terminal_log(active_zone, pred_base, pred_final, last_row)

            # A Influx solo actividad + hora exacta
            write_activity_to_influx(last_row, active_zone, pred_base, pred_final)

            # Manejo de persistencia por actividad
            released = False
            if is_inactive_prediction(active_zone, pred_final):
                inactive_streak[active_zone] += 1
                print(f"⚠ {active_zone} en sin actividad. streak={inactive_streak[active_zone]}")

                if inactive_streak[active_zone] >= MAX_INACTIVE_STREAK:
                    print(f"⛔ Liberando zona activa por inactividad repetida: {active_zone}")
                    active_zone = None
                    active_event_ts = None
                    released = True
            else:
                inactive_streak[active_zone] = 0

            if not released and active_zone is not None:
                last_run_at[active_zone] = now_ts

        except KeyboardInterrupt:
            print("\n⏹ Proceso detenido por el usuario.")
            break
        except Exception as e:
            print(f"\n❌ Error general: {e}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()