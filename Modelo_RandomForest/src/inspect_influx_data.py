from influxdb_client import InfluxDBClient
import pandas as pd

from config_influx import INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET

MEASUREMENT = "Sistema_Casa"


def main():
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -7d)
      |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
      |> limit(n: 300)
    '''

    with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        query_api = client.query_api()
        df = query_api.query_data_frame(query=query, org=INFLUX_ORG)

    if isinstance(df, list):
        df = pd.concat(df, ignore_index=True)

    print("\n===== COLUMNAS =====")
    print(df.columns.tolist())

    print("\n===== PRIMERAS 20 FILAS =====")
    print(df.head(20).to_string())

    for col in ["_measurement", "_field", "node", "zone", "sensor", "metric", "unit"]:
        if col in df.columns:
            print(f"\n===== VALORES ÚNICOS EN {col} =====")
            valores = sorted(df[col].dropna().astype(str).unique().tolist())
            for v in valores[:100]:
                print(v)

    print("\n===== RESUMEN =====")
    print(df.info())


if __name__ == "__main__":
    main()