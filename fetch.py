import streamlit as st
import requests
import json

st.set_page_config(page_title="API Request Builder", layout="wide")

st.title("🔧 API Request Builder & Tester")

# --- SIDEBAR INPUTS ---
st.sidebar.header("Request Builder")

base_url = st.sidebar.text_input("Base URL", "https://api.example.com")
endpoint = st.sidebar.text_input("Endpoint", "/v1/test")

method = st.sidebar.selectbox("Method", ["GET", "POST", "PUT", "PATCH", "DELETE"])

# Headers editor
headers_raw = st.sidebar.text_area("Headers (JSON)", "{\n  \"Content-Type\": \"application/json\"\n}")

# Query params editor
params_raw = st.sidebar.text_area("Query Params (JSON)", "{ }")

# Body editor
body_raw = st.sidebar.text_area("Body (JSON or raw text)", "{ }")

send_button = st.sidebar.button("Send Request 🚀")

# --- MAIN PAGE OUTPUT ---
st.subheader("Response")

if send_button:
    # Parse headers
    try:
        headers = json.loads(headers_raw) if headers_raw.strip() else {}
    except:
        st.error("Invalid JSON in headers.")
        headers = {}

    # Parse query params
    try:
        params = json.loads(params_raw) if params_raw.strip() else {}
    except:
        st.error("Invalid JSON in query params.")
        params = {}

    # Parse body (try JSON first, fallback to raw text)
    try:
        body = json.loads(body_raw)
    except:
        body = body_raw

    url = base_url.rstrip("/") + "/" + endpoint.lstrip("/")

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=body if isinstance(body, dict) else None,
            data=body if isinstance(body, str) else None
        )

        st.code(f"{method} {response.url}", language="bash")

        st.write("### Status")
        st.write(response.status_code)

        st.write("### Headers")
        st.json(dict(response.headers))

        st.write("### Body")
        try:
            st.json(response.json())
        except:
            st.text(response.text)

    except Exception as e:
        st.error(f"Request failed: {e}")

# --- CURL PREVIEW ---
st.subheader("Curl Preview")

curl_headers = " ".join([f"-H '{k}: {v}'" for k, v in (json.loads(headers_raw) if headers_raw else {}).items()])
curl_data = f"-d '{body_raw}'" if body_raw.strip() and method in ["POST", "PUT", "PATCH"] else ""

curl_preview = f"curl -X {method} {curl_headers} {curl_data} '{base_url.rstrip('/')}/{endpoint.lstrip('/')}'"

st.code(curl_preview, language="bash")