import os
import time
import tempfile
import streamlit as st
from PIL import Image

from config import APP_NAME, APP_VERSION, APP_SUBTITLE, INSTITUTION, ENGINES, DEFAULT_ENGINE
from agent.core import ScribeAgent

# Page configuration
st.set_page_config(
    page_title=f"{APP_NAME} v{APP_VERSION}",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if "agent" not in st.session_state:
    st.session_state.agent = ScribeAgent()

# Helper function to save uploaded file
def save_uploaded_file(uploaded_file):
    try:
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    except Exception as e:
        st.error(f"Failed to save file: {e}")
        return None

# Sidebar
with st.sidebar:
    st.title(f"🔬 {APP_NAME}")
    st.caption(f"v{APP_VERSION} · {INSTITUTION}")
    st.caption(APP_SUBTITLE)
    st.divider()

    st.header("Settings")
    
    # Engine selector
    engine_options = {e["key"]: e["label"] for e in ENGINES}
    selected_engine_key = st.selectbox(
        "OCR Engine",
        options=list(engine_options.keys()),
        format_func=lambda x: engine_options[x],
        index=list(engine_options.keys()).index(DEFAULT_ENGINE)
    )
    
    # Set engine
    st.session_state.agent.set_engine(selected_engine_key)
    
    st.divider()
    
    # Connection Check
    if st.button("Check Ollama Connection"):
        with st.spinner("Checking Ollama..."):
            if ScribeAgent().check_ready():
                st.success("Ollama is running!")
            else:
                st.error("Ollama not found. Please start Ollama before extracting.")


# Main Body
st.header("Document Extraction")

uploaded_file = st.file_uploader("Upload Image (JPG, PNG, BMP, TIFF)", type=["jpg", "jpeg", "png", "bmp", "tiff", "webp"])

if uploaded_file is not None:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.image(uploaded_file, caption="Preview", use_container_width=True)
        
    with col2:
        if st.button("⚡ Extract Text", type="primary", use_container_width=True):
            
            # Save the file temporarily
            image_path = save_uploaded_file(uploaded_file)
            
            if image_path:
                status_container = st.empty()
                progress_bar = st.progress(0)
                
                # Callbacks for agent
                def stage_callback(stage_idx):
                    # rough translation of 0..5 stages to progress 0..100
                    progress_bar.progress(min(stage_idx * 20, 100))
                    
                def progress_callback(msg):
                    status_container.info(f"⏳ {msg}")
                
                with st.spinner("Processing..."):
                    result = st.session_state.agent.run(
                        image_path=image_path,
                        progress_cb=progress_callback,
                        stage_cb=stage_callback
                    )
                
                if result.get("success"):
                    progress_bar.progress(100)
                    status_container.success(f"Done in {result['processing_time']}s! (Score: {result['quality']['score']:.0%})")
                    
                    st.divider()
                    
                    quality_score = int(result['quality']['score'] * 100)
                    
                    st.subheader("Results")
                    st.text_area("Extracted & Cleaned Text", value=result["text"], height=300)
                    
                    # Display Stats
                    st.subheader("Extraction Stats")
                    sc1, sc2, sc3 = st.columns(3)
                    sc1.metric("Quality Score", f"{quality_score}%")
                    sc2.metric("Words", result["quality"].get("word_count", 0))
                    sc3.metric("Equations", result["quality"].get("eq_count", 0))
                    
                    # Downloads
                    st.subheader("Downloads")
                    dl1, dl2 = st.columns(2)
                    
                    docx_path = result.get("docx_path")
                    if docx_path and os.path.exists(docx_path):
                        with open(docx_path, "rb") as f:
                            dl1.download_button("📄 Download DOCX", data=f, file_name=os.path.basename(docx_path), mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
                    
                    pdf_path = result.get("pdf_path")
                    if pdf_path and os.path.exists(pdf_path):
                        with open(pdf_path, "rb") as f:
                            dl2.download_button("📕 Download PDF", data=f, file_name=os.path.basename(pdf_path), mime="application/pdf", use_container_width=True)

                else:
                    progress_bar.empty()
                    status_container.error(f"Error: {result.get('error')}")
