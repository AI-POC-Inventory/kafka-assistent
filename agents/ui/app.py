import streamlit as st
import requests

API_URL = "https://kafka-assistant-orchestrator-989713142030.asia-south1.run.app/run"  # your FastAPI endpoint

st.set_page_config(page_title="Kafka Orchestrator", layout="centered")

st.title("⚡ Kafka Assistant Chatbot")

query = st.text_area("Enter your query:")

if st.button("Run"):
    if query.strip() == "":
        st.warning("Please enter a query")
    else:
        with st.spinner("Running orchestrator..."):
            try:
                response = requests.post(
                    API_URL,
                    json={"query": query}
                )

                if response.status_code == 200:
                    data = response.json()

                    st.success("Execution Complete ✅")

                    st.subheader("Query")
                    st.code(data["query"])

                    st.subheader("Result")
                    st.json(data["result"])

                else:
                    st.error(f"Error: {response.text}")

            except Exception as e:
                st.error(f"Failed to connect: {e}")