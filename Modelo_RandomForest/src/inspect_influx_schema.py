from influxdb_client import InfluxDBClient
from config_influx import INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET


def print_table(title, tables, max_rows=20):
    print(f"\n===== {title} =====")
    count = 0
    for table in tables:
        for record in table.records:
            print(record.values)
            count += 1
            if count >= max_rows:
                return


def run_query(query: str):
    with InfluxDBClient(url=http://192.168.0.198:8086, token=TjCiW9kYSgkUcO4O0F_eoGOguac3NitBq_YkguB9EBRtyHcrIV1f8bEX52fmXuack0x1NaTyOm3AxET8KIU82Q==, org=UNICAUCA) as client:
        query_api = client.query_api()
        return query_api.query(query=query, org=INFLUX_ORG)



def main():
    # 1) Measurements
    q_measurements = f'''
    import "influxdata/influxdb/schema"
    schema.measurements(bucket: "{INFLUX_BUCKET}", start: -30d)
    '''

    # 2) Field keys
    q_fields = f'''
    import "influxdata/influxdb/schema"
    schema.fieldKeys(bucket: "{INFLUX_BUCKET}", start: -30d)
    '''

    # 3) Tag keys
    q_tags = f'''
    import "influxdata/influxdb/schema"
    schema.tagKeys(bucket: "{INFLUX_BUCKET}", start: -30d)
    '''

    measurements = run_query(q_measurements)
    fields = run_query(q_fields)
    tags = run_query(q_tags)

    print_table("MEASUREMENTS", measurements)
    print_table("FIELD KEYS", fields)
    print_table("TAG KEYS", tags)


if __name__ == "__main__":
    main()