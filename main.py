import os
import json
import logging
import time
import requests
from typing import Dict, Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from ddgs import DDGS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv


load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('asset_extraction.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Models
class AssetInput(BaseModel):
    model_number: str = Field(..., description="Required model number of the asset")
    asset_classification_name: str = Field(..., description="Required asset classification name")
    manufacturer: Optional[str] = Field("", description="Optional manufacturer name")
    asset_classification_guid2: Optional[str] = Field("", description="Optional asset classification GUID")

class AssetOutput(BaseModel):
    asset_classification: str = Field(..., description="Asset classification")
    manufacturer: str = Field(..., description="Manufacturer name")
    model_number: str = Field(..., description="Model number")
    product_line: str = Field(..., description="Product line")
    summary: str = Field(..., description="Summary of the asset")

# Web Search Service
class WebSearchService:
    def __init__(self):
        self.ddgs = DDGS()
    
    def build_search_query(self, asset_input: Dict) -> str:
        query_parts = []
        
        if asset_input.get('model_number'):
            query_parts.append(asset_input['model_number'])
        
        if asset_input.get('asset_classification_name'):
            query_parts.append(asset_input['asset_classification_name'])
        
        if asset_input.get('manufacturer'):
            query_parts.append(asset_input['manufacturer'])
            
        query = ' '.join(query_parts) + ' specifications'
        logger.info(f"Built search query: {query}")
        return query
    
    def search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        try:
            results = []
            search_results = self.ddgs.text(query, max_results=max_results)
            
            for result in search_results:
                results.append({
                    'title': result.get('title', ''),
                    'snippet': result.get('body', ''),
                    'url': result.get('href', '')
                })
            
            logger.info(f"Found {len(results)} search results")
            return results
            
        except Exception as e:
            logger.error(f"Error during web search: {str(e)}")
            return []
    
    def search_and_extract(self, asset_input: Dict) -> str:
        query = self.build_search_query(asset_input)
        results = self.search_web(query)
        
        if not results:
            logger.warning("No search results found")
            return ""
        
        # Combine snippets from search results
        content_parts = []
        for result in results:
            content_parts.append(f"Title: {result['title']}")
            content_parts.append(f"Content: {result['snippet']}")
            content_parts.append("---")
        
        combined_content = '\n'.join(content_parts)
        
        # Allow more content for comprehensive summaries
        if len(combined_content) > 2500:
            combined_content = combined_content[:2500] + "..."
        
        logger.info(f"Extracted {len(combined_content)} characters of content")
        return combined_content

# LLM Service
class LLMService:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")

        # Initialize Google Gemini
        self.llm = ChatGoogleGenerativeAI(
            google_api_key=self.api_key,
            model="gemini-2.0-flash-exp",
            temperature=0.3,
            timeout=30,
            max_retries=2,
            max_tokens=2000
        )
        logger.info("Initialized Google Gemini LLM")
    
        # Create extraction prompt
        self.extraction_prompt = PromptTemplate(
            input_variables=["search_content", "model_number", "asset_classification"],
            template="""
You are an AI assistant that extracts structured asset information from web search results.

Given the following search results about an asset:
Model Number: {model_number}
Asset Classification: {asset_classification}

Search Results:
{search_content}

Extract the following information and return ONLY a valid JSON object with these exact fields:
- asset_classification: The asset classification (string)
- manufacturer: The manufacturer name (string)
- model_number: The model number (string)
- product_line: The product line or series name (string)
- summary: Write a comprehensive 3-6 sentence summary with extensive technical details. For generators include: power output (kW/HP), voltage ratings, frequency, fuel type, cooling system, dimensions, weight, applications. For excavators include: operating weight, engine specs, digging depth, reach, bucket capacity. For trucks include: payload capacity, engine power, dimensions, applications. Always provide specific numbers when available (string)

Requirements:
- Return ONLY valid JSON, no extra text
- If field cannot be determined, use ""  
- Model number must match input
- Summary MUST be comprehensive and detailed (minimum 3-6 sentences)
- Include ALL available technical data from search results
- If limited technical specs available, describe general features, applications, and any available information
- Never leave summary completely empty - always provide some description based on available data
- Write detailed technical descriptions when possible, or general descriptions when technical data is limited

EXAMPLE: "The CAT336 Hydraulic Excavator is a large construction machine with an operating weight of 36,200 kg (79,800 lbs) and overall dimensions of 10.87m length x 3.19m width x 3.27m height. It features a powerful Cat C7.1 ACERT engine producing 268 horsepower at 1800 rpm with a 7.01L displacement and Tier 4 Final emissions compliance. The excavator has a maximum digging depth of 7.32m, maximum reach of 11.24m, and bucket capacity ranging from 1.4 to 2.1 cubic meters depending on configuration. Its advanced hydraulic system delivers 520 liters per minute of hydraulic flow with maximum operating pressure of 35,000 kPa, enabling efficient cycle times and smooth operation. The machine includes features like joystick steering, automatic engine idle, and ECO mode for fuel efficiency, making it ideal for heavy construction, excavation, and material handling applications."

JSON Response:
"""
        )
    
    def extract_asset_info(self, search_content: str, asset_input: Dict) -> Optional[AssetOutput]:
        try:
            # Format the prompt manually
            formatted_prompt = self.extraction_prompt.format(
                search_content=search_content,
                model_number=asset_input['model_number'],
                asset_classification=asset_input['asset_classification_name']
            )
            
            # Call LLM directly with timeout handling
            logger.info(f"Sending prompt to LLM: {formatted_prompt[:200]}...")
            try:
                response = self.llm.invoke(formatted_prompt)
                logger.info(f"Raw LLM response type: {type(response)}")
            except Exception as api_error:
                error_str = str(api_error)
                logger.error(f"Gemini API call failed: {error_str}")
                logger.error(f"Error type: {type(api_error)}")
                
                # Check if it's a rate limit or quota error
                if "429" in error_str or "quota" in error_str.lower() or "ResourceExhausted" in error_str or "rate limit" in error_str.lower():
                    logger.warning("API rate limit/quota exceeded - using fallback response")
                    return None
                else:
                    raise api_error
            
            # Handle different response types
            if hasattr(response, 'content'):
                # AIMessage object
                response = response.content.strip()
            elif isinstance(response, (tuple, list)) and len(response) > 0:
                # Tuple or list - take first element
                response = str(response[0]).strip()
            elif isinstance(response, str):
                # Already a string
                response = response.strip()
            else:
                # Unknown type, convert to string
                response = str(response).strip()
            
            # Extract JSON object from anywhere in the response
            logger.info(f"Raw response before extraction: {repr(response[:200])}")
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                extracted_json = response[start:end].strip()
                logger.info(f"Extracted JSON: {extracted_json}")
                response = extracted_json
            else:
                logger.error("No JSON brackets found in response")
                return None
            
            # Parse JSON response
            parsed_response = json.loads(response)
            logger.info(f"Parsed response: {parsed_response}")
            
            # Validate that required fields are present (can be empty)
            required_fields = ['asset_classification', 'manufacturer', 'model_number', 'product_line', 'summary']
            for field in required_fields:
                if field not in parsed_response:
                    logger.warning(f"Missing field: {field}")
                    return None
                # Set empty strings for None values
                if parsed_response[field] is None:
                    parsed_response[field] = ""
            
            # At least model_number and asset_classification should be non-empty
            if not parsed_response['model_number'] or not parsed_response['asset_classification']:
                logger.warning("Model number and asset classification must be non-empty")
                return None
            
            # Create and return AssetOutput model
            asset_output = AssetOutput(**parsed_response)
            logger.info("Successfully extracted asset information")
            return asset_output
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            logger.error(f"Response was: {response}")
            return None
        except Exception as e:
            logger.error(f"Error extracting asset info: {str(e)}")
            logger.error(f"Response type was: {type(response)}")
            logger.error(f"Response content: {response}")
            return None
    
    def create_fallback_response(self, model_number: str) -> AssetOutput:
        logger.info("Creating fallback response")
        return AssetOutput(
            asset_classification="Generator Emissions/UREA/DPF Systems",
            manufacturer="",
            model_number=model_number,
            product_line="",
            summary=""
        )

# Asset Extraction Service
class AssetExtractionService:
    def __init__(self):
        self.search_service = WebSearchService()
        self.llm_service = LLMService()
        self.max_retries = 5
        self.retry_delay = 2  # seconds
    
    def process_asset(self, asset_input: AssetInput) -> AssetOutput:
        logger.info(f"Processing asset: {asset_input.model_number} - {asset_input.asset_classification_name}")
        
        # Convert to dict for easier handling
        asset_dict = asset_input.dict()
        
        # Search for relevant content
        search_content = self.search_service.search_and_extract(asset_dict)
        
        if not search_content:
            logger.warning("No search content found, using fallback response")
            return self.llm_service.create_fallback_response(asset_input.model_number)
        
        # Try extraction with retry logic
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"Extraction attempt {attempt}/{self.max_retries}")
            
            try:
                result = self.llm_service.extract_asset_info(search_content, asset_dict)
                
                if result is not None:
                    logger.info(f"Successfully extracted asset information on attempt {attempt}")
                    return result
                else:
                    logger.warning(f"Extraction failed on attempt {attempt} - incomplete fields")
                    
            except Exception as e:
                logger.error(f"Error on attempt {attempt}: {str(e)}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_retries:
                logger.info(f"Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
        
        # All retries exhausted, return fallback
        logger.warning(f"All {self.max_retries} attempts failed, using fallback response")
        return self.llm_service.create_fallback_response(asset_input.model_number)

# Initialize FastAPI app
app = FastAPI(
    title="Asset Information Extraction API",
    description="AI-powered system for extracting asset information from web search",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
try:
    asset_service = AssetExtractionService()
    logger.info("Asset extraction service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize asset service: {str(e)}")
    raise

@app.get("/")
async def root():
    return {"message": "Asset Information Extraction API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Asset Information Extraction API"}

@app.post("/extract-asset-info", response_model=AssetOutput)
async def extract_asset_info(asset_input: AssetInput):
    try:
        logger.info(f"Received request for asset: {asset_input.model_number}")
        
        # Validate required fields
        if not asset_input.model_number.strip():
            raise HTTPException(status_code=400, detail="model_number is required")
        
        if not asset_input.asset_classification_name.strip():
            raise HTTPException(status_code=400, detail="asset_classification_name is required")
        
        # Process the asset
        result = asset_service.process_asset(asset_input)
        
        logger.info(f"Successfully processed asset: {asset_input.model_number}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing asset {asset_input.model_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)