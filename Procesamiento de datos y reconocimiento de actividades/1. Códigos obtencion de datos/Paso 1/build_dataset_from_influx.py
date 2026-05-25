from influxdb_client import InfluxDBClient
import pandas as pd

from config_influx import INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET

MEASUREMENT = "Sistema_Casa"


def clean_name(text):
    return text.lower().replace(" ", "_").replace("-", "_")


def main():
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -2d)
      |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
    '''

    with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        query_api = client.query_api()
        df = query_api.query_data_frame(query=query, org=INFLUX_ORG)

    if isinstance(df, list):
        df = pd.concat(df, ignore_index=True)

    print("Datos cargados:", df.shape)

    # Crear nombre de variable
    df["var"] = (
        df["zone"].apply(clean_name) + "_" +
        df["sensor"].apply(clean_name) + "_" +
        df["metric"].apply(clean_name)
    )

    # Usar timestamp
    df["timestamp"] = df["_time"]

    # Pivotear (transformar a columnas)
    df_pivot = df.pivot_table(
        index="timestamp",
        columns="var",
        values="_value",
        aggfunc="last"
    )

    df_pivot = df_pivot.reset_index()

    print("\nDataset generado:")
    print(df_pivot.head())

    print("\nTotal columnas:", len(df_pivot.columns))

    # Guardar CSV
    df_pivot.to_csv("data/dataset_real2.csv", index=False)

    print("\n✅ Dataset guardado en data/dataset_real2.csv")


if __name__ == "__main__":
    main()