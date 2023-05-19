# Leaf Disease Severity Prediction Bridge

Simple app to calculate severity of leaf disease according to https://apsjournals.apsnet.org/doi/10.1094/PDIS-02-20-0262-RE.

It reads data (temperature and leaf wetness) from InfluxDB and writes back calculated disease severity to InfluxDB.

## How to run

* just run container with environment variable `INFLUXDB_TOKEN`:

```bash
docker pull approximatenumber/leaf-disease-predictor:latest  # you can use tag instead of 'latest'
docker run -e INFLUXDB_TOKEN="SECRET" approximatenumber/leaf-disease-predictor:latest
```
