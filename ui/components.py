import streamlit as st


def display_chat_history(messages):
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def display_execution_details(result):
    with st.expander("🔍 Execution Details"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Processing Mode", result.get("processing_mode", "unknown"))
        with col2:
            st.metric("Elapsed Time", f"{result.get('elapsed', 0):.2f}s")
        with col3:
            st.metric("Artifacts", len(result.get("artifacts", [])))

        if result.get("understanding"):
            st.subheader("Understanding")
            st.json(result["understanding"].model_dump())

        if result.get("web_search_results"):
            st.subheader("Web Search")
            st.write(f"Found {len(result['web_search_results'].results)} results")

        if result.get("reflection"):
            st.subheader("Reflection")
            st.json(result["reflection"].model_dump())
