import boto3, io, json
import pandas as pd
import streamlit as st

def _s3():
    try:
        creds = st.secrets["aws"]
        return boto3.client("s3", region_name=creds["AWS_DEFAULT_REGION"],
                            aws_access_key_id=creds["AWS_ACCESS_KEY_ID"],
                            aws_secret_access_key=creds["AWS_SECRET_ACCESS_KEY"])
    except Exception:
        return boto3.client("s3", region_name="us-east-1")

def _bucket():
    try:
        return st.secrets["aws"]["S3_BUCKET"]
    except Exception:
        return "osint-monitor-data"

@st.cache_data(ttl=300)
def load_table(table_name):
    try:
        obj = _s3().get_object(Bucket=_bucket(), Key=f"tables/{table_name}.parquet")
        return pd.read_parquet(io.BytesIO(obj["Body"].read()))
    except Exception as e:
        if "NoSuchKey" not in str(e):
            st.warning(f"Could not load {table_name}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_manifest():
    try:
        obj = _s3().get_object(Bucket=_bucket(), Key="manifest.json")
        return json.loads(obj["Body"].read())
    except Exception:
        return {"last_sync": "unknown", "total_rows": 0}

def load_all():
    return {
        "messages":        load_table("messages"),
        "classifications": load_table("classifications"),
        "entities":        load_table("entities"),
        "crypto":          load_table("crypto_addresses"),
        "channel_runs":    load_table("channel_runs"),
    }
