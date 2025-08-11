# Asset Information Extraction System

AI-powered system that extracts structured asset information using web search and Large Language Model processing. Built with FastAPI backend, Streamlit frontend, and Google Gemini for AI processing.

## Features

- **Web Search Integration**: Automatically searches for asset information online using DuckDuckGo
- **AI Processing**: Uses Google Gemini to extract structured data from search results
- **Retry Logic**: Up to 5 retry attempts with intelligent fallback mechanism
- **Real-time Processing**: Fast API endpoints with comprehensive logging
- **Simple Interface**: Clean web interface for easy interaction
- **Robust Error Handling**: Comprehensive error handling and logging throughout

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit     │    │    FastAPI       │    │   Google        │
│   Frontend      │◄──►│    Backend       │◄──►│   Gemini        │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Web Search     │
                       │  (DuckDuckGo)    │
                       └──────────────────┘
```

## Requirements

- Python 3.8+
- Google API Key for Gemini
- Internet connection for web search

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the API Server

```bash
python main.py
```

The API server will start at `http://localhost:8002`

### 3. Start the Frontend

In a new terminal:

```bash
streamlit run app.py
```

The web interface will open at `http://localhost:8501`

## Usage

### Web Interface

1. Open the Streamlit app in your browser
2. Enter required fields:
   - **Model Number**: e.g., "MRN85HD"
   - **Asset Classification**: e.g., "Generator (Marine)"
   - **Manufacturer**: (optional)
3. Click "Extract Asset Information"
4. View the structured results

### API Usage

**Input Format:**
```json
{
  "model_number": "MRN85HD",
  "asset_classification_name": "Generator (Marine)",
  "manufacturer": "",
  "asset_classification_guid2": ""
}
```

**Output Format:**
```json
{
  "asset_classification": "Marine Generator",
  "manufacturer": "WhisperPower",
  "model_number": "MRN85HD",
  "product_line": "",
  "summary": "Detailed technical summary with specifications..."
}
```

**API Endpoints:**
- `GET /`: Health check
- `GET /health`: Detailed health status
- `POST /extract-asset-info`: Main extraction endpoint

## How It Works

1. **Input Processing**: Receives asset information (model number, classification, etc.)
2. **Web Search**: Builds search queries and finds relevant product information online
3. **Content Extraction**: Extracts and cleans relevant content from search results
4. **AI Processing**: Uses Google Gemini to extract structured information
5. **Retry Logic**: Attempts extraction up to 5 times if incomplete results
6. **Fallback**: Returns default response if all attempts fail

## Project Structure

```
asset-extraction-system/
├── main.py              # Complete FastAPI application with all services
├── app.py               # Simple Streamlit frontend
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Configuration

The Google API key is configured directly in the code. To use your own key, update the `api_key` variable in the `LLMService` class in `main.py`.

### Retry Configuration

- **Max Retries**: 5 attempts
- **Retry Delay**: 2 seconds between attempts
- **Fallback Response**: Default classification when all retries fail

### Logging

Logs are written to:
- Console output
- `asset_extraction.log` file

## Example

### Using the Web Interface

1. Model Number: `MRN85HD`
2. Asset Classification: `Generator (Marine)`
3. Click "Extract Asset Information"

**Result:**
```json
{
  "asset_classification": "Generator (Marine)",
  "manufacturer": "WhisperPower",
  "model_number": "MRN85HD",
  "product_line": "",
  "summary": "The MRN85HD is a marine generator featuring silent operation, diesel engine, and compact design for marine applications..."
}
```

### Using API Directly

```python
import requests

payload = {
    "model_number": "MRN85HD",
    "asset_classification_name": "Generator (Marine)",
    "manufacturer": ""
}

response = requests.post("http://localhost:8000/extract-asset-info", json=payload)
print(response.json())
```

## Error Handling

The system includes comprehensive error handling:

- **Input Validation**: Required field validation with error messages
- **Connection Errors**: Graceful handling of network issues
- **AI Failures**: Retry logic with fallback responses
- **Search Failures**: Fallback when web search fails
- **Timeout Handling**: Request timeouts to prevent hanging

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   - Kill the process using the port or change the port in the code

2. **Connection Refused**
   - Make sure the API server is running before starting the frontend

3. **Search Results Empty**
   - Check internet connection
   - Try different search terms

4. **AI Extraction Fails**
   - Check API key validity
   - Monitor rate limits
   - Review logs for detailed error messages

### Debug Mode

All operations are logged with detailed information including:
- Input received
- Search results found
- Extraction attempts
- Retry information
- Fallback triggers
- Error details
