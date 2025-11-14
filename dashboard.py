# dashboard.py
import streamlit as st

st.set_page_config(
    page_title="BattleBots Dashboard",
    layout="wide",
    page_icon="🤖"
)

st.title("🤖 Welcome to your AI Bot Dashboard")
st.caption("Select an application from the sidebar to get started.")

st.header("Available Apps")

col1, col2 = st.columns(2)

with col1:
    # This links to the app you moved
    st.page_link(
        "pages/1_Debate_App.py", 
        label="Battle of the Bots", 
        icon="🗣️"
    )
    st.markdown("Run a multi-round, structured debate between two models with a critic.")

with col2:
    # This links to the app you moved
    st.page_link(
        "pages/2_Model_Comparator.py", 
        label="A/B Model Test", 
        icon="🔄"
    )
    st.markdown("Compare two models side-by-side with a single prompt and a critic's verdict.")

# This links to the new file we are about to create
st.page_link(
    "pages/3_Model_Explorer.py", 
    label="Model Explorer", 
    icon="🔍"
)
st.markdown("View your locally installed models and pull new models from the Ollama library.")


st.header("About This Project")
st.markdown("""
This project is a local-first environment for testing and experimenting with offline language models using `Ollama` and `Streamlit`.
""")
