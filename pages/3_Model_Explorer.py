# pages/3_Model_Explorer.py
import streamlit as st
import subprocess
import re
import pandas as pd
import time

st.set_page_config(page_title="Model Explorer", layout="wide")
st.title("🔍 Model Explorer")

# --- This is our "database" of popular models, now with links ---
CURATED_MODEL_LIST = [
    {
        "name": "llama3.1:8b",
        "tags": ["General Purpose", "New"],
        "description": "Meta's newest, state-of-the-art 8B model. Excellent for general chat, reasoning, and code.",
        "ollama_link": "https://ollama.com/library/llama3.1",
        "hf_link": "https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct"
    },
    {
        "name": "mistral:7b",
        "tags": ["General Purpose", "Fast"],
        "description": "The classic 7B model. Famous for its high performance at a small size. A great all-rounder.",
        "ollama_link": "https://ollama.com/library/mistral",
        "hf_link": "https://huggingface.co/mistralai/Mistral-7B-v0.1"
    },
    {
        "name": "codellama:7b",
        "tags": ["Coding"],
        "description": "A Llama model fine-tuned specifically for code generation, completion, and debugging.",
        "ollama_link": "https://ollama.com/library/codellama",
        "hf_link": "https://huggingface.co/codellama/CodeLlama-7b-hf"
    },
    {
        "name": "deepseek-coder:6.7b",
        "tags": ["Coding", "Fast"],
        "description": "A very strong model built specifically for code generation. Many devs prefer it over Codellama.",
        "ollama_link": "https://ollama.com/library/deepseek-coder",
        "hf_link": "https://huggingface.co/deepseek-ai/deepseek-coder-6.7b-instruct"
    },
    {
        "name": "phi3:mini",
        "tags": ["Small", "Fast"],
        "description": "Microsoft's 3.8B model. Very capable for its size, designed to run on-device.",
        "ollama_link": "https://ollama.com/library/phi3",
        "hf_link": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct"
    },
    {
        "name": "gemma2:2b",
        "tags": ["Small", "Fast", "New"],
        "description": "Google's new 2B model. Highly efficient and a great choice for lightweight tasks.",
        "ollama_link": "https://ollama.com/library/gemma2",
        "hf_link": "https://huggingface.co/google/gemma-2b"
    },
    {
        "name": "llava:7b",
        "tags": ["Multimodal", "Vision"],
        "description": "A multimodal model that can understand **images and text**. Give it a URL or upload an image and ask questions.",
        "ollama_link": "https://ollama.com/library/llava",
        "hf_link": "https://huggingface.co/llava-hf/llava-1.5-7b-hf"
    },
]

# --- Helper function to get *local* models ---
@st.cache_data(ttl=60) # Cache for 60 seconds
def get_local_models():
    """
    Runs 'ollama list' and returns a simple list of model names.
    """
    model_names = []
    try:
        result = subprocess.run(
            ["ollama", "list"], 
            capture_output=True, text=True, check=True, encoding='utf-8'
        )
        lines = result.stdout.strip().split('\n')
        
        if len(lines) > 1:
            for line in lines[1:]:
                parts = re.split(r'\s+', line.strip())
                if len(parts) >= 1:
                    model_names.append(parts[0])
    except Exception as e:
        # Don't show error here, show it in the main table function
        pass
    return model_names

# --- Helper function to get local models as a DataFrame ---
@st.cache_data(ttl=60)
def get_local_models_df():
    """
    Runs 'ollama list' and parses the output into a DataFrame.
    """
    models = []
    try:
        result = subprocess.run(
            ["ollama", "list"], 
            capture_output=True, text=True, check=True, encoding='utf-8'
        )
        lines = result.stdout.strip().split('\n')
        
        if len(lines) <= 1:
            return pd.DataFrame(columns=["Name", "Size", "Modified"])

        for line in lines[1:]:
            parts = re.split(r'\s+', line.strip())
            if len(parts) >= 4:
                name, model_id, size, unit = parts[0], parts[1], parts[2], parts[3]
                modified = " ".join(parts[4:])
                models.append({
                    "Name": name, "Size": f"{size} {unit}", "Modified": modified, "ID": model_id
                })
        return pd.DataFrame(models)
                        
    except Exception as e:
        st.error(f"Error running 'ollama list': {e}")
        return pd.DataFrame(columns=["Name", "Size", "Modified"])

def pull_model(model_name):
    """Pulls a model and streams the output to the UI."""
    with st.status(f"Pulling {model_name}...", expanded=True) as status:
        output_container = st.empty()
        full_output = ""
        try:
            cmd = ["ollama", "pull", model_name]
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                text=True, encoding='utf-8'
            )
            for line in iter(process.stdout.readline, ''):
                full_output += line
                output_container.code(full_output, language='bash')
            process.stdout.close()
            process.wait()
            
            if process.returncode == 0:
                status.update(label=f"Successfully pulled {model_name}!", state="complete")
                st.toast("Model pull complete!", icon="✅")
                st.cache_data.clear() # Clear all caches
                st.cache_resource.clear()
                time.sleep(1)
                st.rerun() # Rerun to update the "Installed" status
            else:
                status.update(label=f"Failed to pull {model_name}.", state="error")
                st.error("Pull failed. See output above.")
        except Exception as e:
            status.update(label="Pull failed.", state="error")
            st.error(f"An error occurred: {e}")

# --- NEW: Helper function to delete a local model ---
def delete_model(model_name):
    """Deletes a model and streams the output to the UI."""
    with st.status(f"Deleting {model_name}...", expanded=True) as status:
        try:
            cmd = ["ollama", "rm", model_name]
            result = subprocess.run(
                cmd, 
                capture_output=True, text=True, check=True, encoding='utf-8'
            )
            
            status.update(label=f"Successfully deleted {model_name}!", state="complete")
            st.toast("Model deleted!", icon="🗑️")
            st.cache_data.clear() # Clear all caches
            st.cache_resource.clear()
            time.sleep(1)
            st.rerun() # Rerun to update all model lists
            
        except subprocess.CalledProcessError as e:
            status.update(label=f"Failed to delete {model_name}.", state="error")
            st.error(f"Deletion failed: {e.stderr}")
        except Exception as e:
            status.update(label="Deletion failed.", state="error")
            st.error(f"An error occurred: {e}")
# --- END NEW FUNCTION ---

# --- Main Page ---
st.header("Model Discovery Links")
st.markdown("""
- **[Ollama Library](https://ollama.com/library)**: The official library of models pre-packaged for Ollama.
- **[Hugging Face Models Hub](https://huggingface.co/models)**: The main repository for *all* open-source models.
- **[Open LLM Leaderboard](https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard)**: Ranks and evaluates open LLMs for performance.
""")
st.divider()

st.header("Pull Any Model")
st.markdown("Enter any model name from the **official [Ollama Library](https://ollama.com/library)** to pull it. This will not work for Hugging Face models that are not in the library.")
model_to_pull = st.text_input("Model Name to Pull", placeholder="e.g., llama3.1:70b or gemma2:2b")
if st.button(f"Pull '{model_to_pull}'"):
    if not model_to_pull:
        st.warning("Please enter a model name to pull.")
    else:
        pull_model(model_to_pull)
st.divider()

st.header("Explore Curated Models")
all_tags = sorted(list(set(tag for model in CURATED_MODEL_LIST for tag in model["tags"])))
selected_tags = st.multiselect("Filter by specialty:", all_tags)
local_models_list = get_local_models()
st.markdown("---")

for model in CURATED_MODEL_LIST:
    if selected_tags and not all(tag in model["tags"] for tag in selected_tags):
        continue

    col1, col2 = st.columns([3, 1]) 
    with col1:
        st.subheader(model["name"])
        tag_html = "".join([f"<span style='background-color:#444; color:#FFF; padding: 2px 8px; border-radius: 5px; margin-right: 5px;'>{tag}</span>" for tag in model["tags"]])
        st.markdown(tag_html, unsafe_allow_html=True)
        st.markdown(model["description"])
    
    with col2:
        st.markdown(f"[View on Ollama Library]({model['ollama_link']})", unsafe_allow_html=True)
        st.markdown(f"[View on Hugging Face]({model['hf_link']})", unsafe_allow_html=True)
        
        is_installed = model["name"] in local_models_list
        button_key = f"pull-{model['name']}"
        
        if is_installed:
            st.button("✅ **Installed**", key=button_key, disabled=True, use_container_width=True)
        else:
            if st.button(f"Pull", key=button_key, use_container_width=True):
                pull_model(model["name"])
    
    st.markdown("---")

# --- Section 3: My Locally Installed Models (UPDATED) ---
st.header("My Locally Installed Models")
st.markdown("This list updates automatically when you pull or delete a model.")

model_df = get_local_models_df()
if model_df.empty:
    st.warning("No local Ollama models found.")
else:
    # Create a dynamic list instead of a static dataframe
    
    # 1. Create Headers
    header_cols = st.columns([3, 2, 3, 1])
    header_cols[0].markdown("**Name**")
    header_cols[1].markdown("**Size**")
    header_cols[2].markdown("**Modified**")
    header_cols[3].markdown("**Action**")
    st.divider()

    # 2. Loop through the DataFrame and create a row for each model
    for index, row in model_df.iterrows():
        model_name = row["Name"]
        cols = st.columns([3, 2, 3, 1])
        
        cols[0].markdown(model_name)
        cols[1].markdown(row["Size"])
        cols[2].markdown(row["Modified"])
        
        # Add the delete button
        if cols[3].button("Delete", key=f"del_{model_name}", use_container_width=True):
            delete_model(model_name)

# --- END OF UPDATE ---
