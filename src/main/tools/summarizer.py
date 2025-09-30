from openai import OpenAI
import os
import json
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client with Ollama base URL
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="fake-key"
)

class SummaryConfig:
    """Configuration for text summarization"""
    def __init__(
        self,
        model: str = "gpt-oss:20b",  # Default to mistral model
        temperature: float = 0.7,
        max_tokens: int = 1000,
        length: str = "medium"  # short, medium, long
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.length = length

def create_summary_prompt(text: str, length: str = "medium") -> str:
    """Create a prompt for summarization based on desired length"""
    length_guides = {
        "short": "Create a brief 2-3 sentence summary of the following text",
        "medium": "Create a comprehensive paragraph summarizing the key points of the following text",
        "long": "Create a detailed summary of the following text, capturing main points and important details"
    }

    base_prompt = length_guides.get(length, length_guides["medium"])
    return f"{base_prompt}:\n\n{text}"

def summarize_text(
    text: str,
    config: Optional[SummaryConfig] = None
) -> str:
    """
    Generate a summary of the given text using Ollama through OpenAI API compatibility.

    Args:
        text: The text to summarize
        config: Optional configuration for the summarization

    Returns:
        str: The generated summary
    """
    if config is None:
        config = SummaryConfig()

    try:
        logger.info(f"Generating summary using model: {config.model}")
        logger.info(f"Text length: {len(text)} characters")

        # Create the completion request
        response = client.chat.completions.create(
            model=config.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a skilled assistant specialized in creating clear and concise summaries."
                },
                {
                    "role": "user",
                    "content": create_summary_prompt(text, config.length)
                }
            ],
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
        logger.info(f"received: {response} from model")
        # Extract the summary from the response
        summary = response.choices[0].message.content.strip()
        logger.info("Summary generated successfully")
        logger.debug(f"Summary length: {len(summary)} characters")
        return summary

    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise Exception(f"Error generating summary: {str(e)}")

def chunk_long_text(text: str, max_chunk_size: int = 4000) -> list[str]:
    """
    Split long text into smaller chunks for processing

    Args:
        text: The text to split
        max_chunk_size: Maximum size of each chunk in characters

    Returns:
        list[str]: List of text chunks
    """
    logger.info(f"Chunking text of length {len(text)} with max chunk size {max_chunk_size}")
    # Split text into sentences (naive approach - can be improved)
    sentences = text.replace("! ", "!|").replace("? ", "?|").replace(". ", ".|").split("|")

    chunks = []
    current_chunk = []
    current_size = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # If adding this sentence would exceed max size, save current chunk and start new one
        if current_size + len(sentence) > max_chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_size = 0

        current_chunk.append(sentence)
        current_size += len(sentence) + 1  # +1 for space

    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    logger.info(f"Text split into {len(chunks)} chunks")
    return chunks

def summarize_long_text(
    text: str,
    config: Optional[SummaryConfig] = None
) -> str:
    """
    Summarize a long text by chunking it and summarizing each chunk

    Args:
        text: The long text to summarize
        config: Optional configuration for the summarization

    Returns:
        str: Combined summary of all chunks
    """
    logger.info("Starting long text summarization")
    if config is None:
        config = SummaryConfig()

    # Split text into chunks
    chunks = chunk_long_text(text)

    if len(chunks) == 1:
        logger.info("Text fits in single chunk, summarizing directly")
        return summarize_text(chunks[0], config)

    # Summarize each chunk
    logger.info(f"Processing {len(chunks)} chunks")
    chunk_summaries = []
    for i, chunk in enumerate(chunks, 1):
        logger.info(f"Summarizing chunk {i}/{len(chunks)}")
        chunk_config = SummaryConfig(
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens // 2,
            length="short"
        )
        chunk_summary = summarize_text(chunk, chunk_config)
        chunk_summaries.append(chunk_summary)

    # Combine chunk summaries and create final summary
    logger.info("Generating final summary from chunk summaries")
    combined_text = " ".join(chunk_summaries)
    return summarize_text(combined_text, config)

def auto_summarize(text: str, config: Optional[SummaryConfig] = None) -> str:
    """
    Automatically choose between regular and long text summarization based on text length.

    Args:
        text: The text to summarize
        config: Optional configuration for the summarization

    Returns:
        str: The generated summary
    """
    if config is None:
        config = SummaryConfig()

    text_length = len(text)
    logger.info(f"Auto-selecting summarization method for text of length {text_length}")

    # If text is longer than 2000 characters, use long text summarization
    if text_length > 2000:
        logger.info("Using long text summarization method")
        return summarize_long_text(text, config)
    else:
        logger.info("Using regular summarization method")
        return summarize_text(text, config)

# Example usage
if __name__ == "__main__":
    logger.info("This module provides text summarization functionality.")
    logger.info("For usage examples, see test_summarizer.py")
