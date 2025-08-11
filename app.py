import streamlit as st
import requests
import json
from typing import Dict, Any

# Configure page
st.set_page_config(
    page_title="Asset Information Extraction",
    page_icon="🔍",
    layout="wide"
)

# Constants
API_BASE_URL = "http://localhost:8002"

def call_api(asset_data: Dict[str, Any]) -> Dict[str, Any]:
    """Call the FastAPI backend"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/extract-asset-info",
            json=asset_data,
            timeout=60
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {
                "success": False, 
                "error": f"API Error: {response.status_code} - {response.text}"
            }
            
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Connection Error: Could not connect to API server. Make sure the API server is running on localhost:8000"
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Timeout Error: The request took too long to complete"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }

def main():
    # Header
    st.title("Asset Information Extraction System")
    st.markdown("AI-powered system that extracts structured asset information using web search and LLM processing")
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("Asset Input")
        
        # Input form
        with st.form("asset_form"):
            model_number = st.text_input(
                "Model Number *", 
                placeholder="e.g., MRN85HD"
            )
            
            asset_classification = st.text_input(
                "Asset Classification Name *", 
                placeholder="e.g., Generator (Marine)"
            )
            
            manufacturer = st.text_input(
                "Manufacturer", 
                placeholder="e.g., Cummins (optional)"
            )
            
            submitted = st.form_submit_button("Extract Asset Information", use_container_width=True)
    
    with col2:
        st.header("Extraction Results")
        
        if submitted:
            # Validate required fields
            if not model_number.strip():
                st.error("Model Number is required")
                return
                
            if not asset_classification.strip():
                st.error("Asset Classification Name is required")
                return
            
            # Prepare API payload
            payload = {
                "model_number": model_number.strip(),
                "asset_classification_name": asset_classification.strip(),
                "manufacturer": manufacturer.strip(),
                "asset_classification_guid2": ""
            }
            
            # Call API with loading spinner
            with st.spinner("Searching web and extracting information..."):
                result = call_api(payload)
            
            # Display results
            if result["success"]:
                st.success("Asset information extracted successfully!")
                
                data = result["data"]
                
                # Display structured output
                st.subheader("Structured Output")
                
                # Create a nice display of the results
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.metric("Asset Classification", data.get("asset_classification", "N/A"))
                    st.metric("Model Number", data.get("model_number", "N/A"))
                
                with col_b:
                    st.metric("Manufacturer", data.get("manufacturer", "N/A"))
                    st.metric("Product Line", data.get("product_line", "N/A"))
                    
                # Summary
                st.subheader("Summary")
                summary = data.get("summary", "No summary available")
                if summary:
                    st.write(summary)
                else:
                    st.info("No summary information was extracted")
                
                # Raw JSON output
                with st.expander("Raw JSON Output"):
                    st.json(data)
                    
            else:
                st.error(f"Error: {result['error']}")

if __name__ == "__main__":
    main()