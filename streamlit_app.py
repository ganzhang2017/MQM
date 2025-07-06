import streamlit as st
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader # For PDF parsing
from pptx import Presentation # For PPTX parsing (requires python-pptx)
import io
import os

from openai import OpenAI # Activating OpenAI

# --- API Key Configuration ---
# IMPORTANT: Do NOT hardcode your API key here.
# Use Streamlit Secrets for production deployment.

def extract_text_from_pdf(uploaded_file):
    try:
        reader = PdfReader(io.BytesIO(uploaded_file.read()))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"Error extracting PDF: {e}"

def extract_text_from_pptx(uploaded_file):
    try:
        prs = Presentation(io.BytesIO(uploaded_file.read()))
        text = ""
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
        return text
    except Exception as e:
        return f"Error extracting PPTX: {e}"

def scrape_website_text(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.content, 'html.parser')
        # Attempt to extract main content, often found in <article>, <main>, or common content divs
        main_content = soup.find('article') or soup.find('main') or soup.find('div', class_='content')
        if main_content:
            return main_content.get_text(separator='\n', strip=True)
        else:
            # Fallback to extracting all visible text if specific content area not found
            texts = soup.stripped_strings
            return "\n".join(texts)
    except requests.exceptions.RequestException as e:
        st.error(f"Error accessing website {url}: {e}")
        return ""
    except Exception as e:
        st.error(f"Error parsing website {url}: {e}")
        return ""

def generate_memo_section_llm(section_name, prompt, document_text, api_key):
    """
    Generates a memo section using an LLM via OpenRouter.
    This function requires a valid OpenRouter API key.
    """
    if not api_key:
        return f"Please provide an API key in Streamlit secrets to generate {section_name}."

    try:
        # Initialize OpenAI client to connect to OpenRouter
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1", # OpenRouter's API endpoint
            api_key=api_key,
            # Optional: OpenRouter often uses these for analytics/ranking
            default_headers={
                # IMPORTANT: Replace with your actual Streamlit app URL for OpenRouter's analytics
                "HTTP-Referer": "https://your-streamlit-app-url.streamlit.app/",
                "X-Title": "AI Investment Memo Generator",
            }
        )

        # Using "anthropic/claude-3-5-sonnet" as the model via OpenRouter
        model_to_use = "anthropic/claude-3-5-sonnet"

        response = client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "system", "content": "You are an expert investment analyst assistant. Your task is to extract and summarize information from provided documents to create sections of an investment memo. Be concise, factual, and directly answer the prompt based *only* on the provided text."},
                {"role": "user", "content": f"{prompt}\n\nHere is the relevant document text to analyze:\n\n{document_text}"}
            ],
            temperature=0.7, # Adjust creativity; 0.7 is a good balance
            max_tokens=1000 # Limit response length to avoid excessive cost/length
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error generating {section_name}: {e}")
        return f"Could not generate {section_name}. Error: {e}"

# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("AI-Powered Investment Memo Generator")
st.markdown("""
Upload a company's pitch deck (PDF/PPTX) and/or provide their website URL to generate an investment memo.
The AI will extract key information, and you'll have the opportunity to review and edit it before finalizing.
""")

# When deployed to Streamlit Cloud, the API key will be loaded from secrets.toml
# Ensure your secret is named "openai_api_key" (or "openrouter_api_key" if you rename it
