import base64
import os
import sys
from typing import Optional
from datetime import datetime

sys.path.append('../')

def get_financial_year() -> str:
    """Get the current financial year in YY-YY format."""
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # If we're in Jan-Mar, we're in the previous year's financial year
    if current_month <= 3:
        year1 = str(current_year - 1)[-2:]
        year2 = str(current_year)[-2:]
    else:
        year1 = str(current_year)[-2:]
        year2 = str(current_year + 1)[-2:]
    
    return f"{year1}-{year2}"

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

from Exceptions import DataError
from .name_matcher import NameMatcher

load_dotenv()

class InvoiceData(BaseModel):
    """Data model for invoice information."""
    supplier_name: str = Field(description="Raw OCR text for supplier name")
    supplier_name_matched: Optional[str] = Field(description="Matched supplier name from database")
    party_name: Optional[str] = Field(description="Raw OCR text for party name")
    party_name_matched: Optional[str] = Field(description="Matched party name from database")
    date: str = Field(description="Date in yyyy-MM-dd format")
    bill_number: str = Field(description="Bill or invoice number")
    amount: int = Field(description="Total amount")

class InvoiceParser:
    def __init__(self):
        """Initialize the invoice parser with LangChain components."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=api_key,
            max_tokens=300,
            temperature=0
        )
        
        self.output_parser = PydanticOutputParser(pydantic_object=InvoiceData)
        self.prompt = self._create_prompt()
        self.bill_number_prompt = self._create_bill_number_prompt()

    def _create_bill_number_prompt(self) -> ChatPromptTemplate:
        """Create the prompt template for bill number processing."""
        template = """You are an expert in analyzing Indian business invoice numbers.

        Context:
        - Supplier Name: {supplier_name}
        - Current Year: {current_year}
        - Current Financial Year: {financial_year}
        - Invoice Number: {bill_number}

        Different suppliers use different formats:
        - Some include their company initials (e.g., if supplier is "Rachit Fashion", they might use "RF/123")
        - Some include the current year or financial year (e.g., "123/23-24" or "2023/456")
        - Some use their location or branch codes
        - Some use separators like "-", "/", or "_"

        Given the supplier name and current year context, extract what appears to be the actual sequential bill number.
        Ignore:
        - Company initials (especially if they match the supplier name's initials)
        - Year indicators (current year or financial year)
        - Branch/location codes
        - Other prefixes/suffixes

        Return only the numeric bill number that uniquely identifies this bill in the supplier's sequence.
        If unsure, return the original number.

        Response format: single line with just the number"""
        
        return ChatPromptTemplate.from_messages([
            ("system", template),
            ("human", "Process this invoice number with the given context.")
        ])

    def process_bill_number(self, bill_number: str, supplier_name: str) -> str:
        """Process bill number using AI to extract the core numeric identifier.
        
        Args:
            bill_number: The original bill number from OCR
            
        Returns:
            Processed bill number (just the core numeric part)
        """
        # If it's already purely numeric, return as is
        if bill_number.isdigit():
            return bill_number
            
        try:
            # Debug output
            print(f"\n=== Bill Number Processing ===")
            print(f"Original bill number: {bill_number}")
            print(f"Supplier name: {supplier_name}")
            
            # Get current year and financial year
            current_year = str(datetime.now().year)
            financial_year = get_financial_year()
            
            print(f"Current year: {current_year}")
            print(f"Financial year: {financial_year}")
            
            # Format the prompt with all context
            messages = self.bill_number_prompt.format_messages(
                bill_number=bill_number,
                supplier_name=supplier_name,
                current_year=current_year,
                financial_year=financial_year
            )
            
            # Get AI response
            response = self.llm.invoke(messages)
            processed_number = response.content.strip()
            
            # Debug output
            print(f"Processed bill number: {processed_number}")
            
            return processed_number if processed_number else bill_number
            
        except Exception as e:
            print(f"Error processing bill number: {str(e)}")
            return bill_number

    def _create_prompt(self) -> ChatPromptTemplate:
        """Create the prompt template for invoice parsing."""
        template = """Extract the following information from the invoice image:
        - Supplier name (sender)
        - Party name (receiver)
        - Date (convert to yyyy-MM-dd format)
        - Bill/invoice number
        - Total amount (as integer)

        {format_instructions}

        If any field is not found, use null for party_name or appropriate empty values for other fields.
        """
        
        return ChatPromptTemplate.from_messages([
            ("system", template),
            ("human", "Process this invoice image and extract the required information.")
        ]).partial(format_instructions=self.output_parser.get_format_instructions())

    def encode_image(self, image_path: str) -> str:
        """Encode an image file to base64 string."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def parse_invoice(self, encoded_image: str) -> dict:
        """Parse invoice information from a base64 encoded image."""
        try:
            # Prepare the message with image
            messages = self.prompt.format_messages()
            messages[1].content = [
                {
                    "type": "text",
                    "text": messages[1].content
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{encoded_image}"
                    }
                }
            ]

            # Get response from LLM
            response = self.llm.invoke(messages)
            
            # Parse and validate the response
            parsed_data = self.output_parser.parse(response.content)
            
            # Convert to dict and process bill number
            result = parsed_data.model_dump()
            if result.get('bill_number'):
                result['bill_number'] = self.process_bill_number(
                    result['bill_number'],
                    result.get('supplier_name', '')  # Pass supplier name for context
                )
            
            return result

        except Exception as e:
            print(f"Error parsing invoice: {str(e)}")
            raise DataError({"status": "error", "message": f"Error parsing invoice: {str(e)}"})

def parse_register_entry(encoded_image: str, cache_file: Optional[str] = None, queue_mode: bool = False) -> dict:
    """Main function to parse register entries from images."""
    try:
        # Parse invoice using OCR
        parser = InvoiceParser()
        result = parser.parse_invoice(encoded_image)
        
        # Debug output for OCR result
        print("\n=== OCR Output ===")
        print(f"Raw OCR result: {result}")
        
        # Initialize name matcher
        matcher = NameMatcher()
        
        # Debug output before name matching
        print("\n=== Name Matching ===")
        print(f"Original supplier name: {result.get('supplier_name')}")
        print(f"Original party name: {result.get('party_name')}")
        
        # Match supplier name if present
        if result.get('supplier_name'):
            matched_supplier = matcher.find_match(result['supplier_name'], 'supplier')
            result['supplier_name_matched'] = matched_supplier if matched_supplier else result['supplier_name']
        
        # Match party name if present
        if result.get('party_name'):
            matched_party = matcher.find_match(result['party_name'], 'party')
            result['party_name_matched'] = matched_party if matched_party else result['party_name']
        
        # Debug output after name matching
        print("\n=== Final Results ===")
        print(f"Matched supplier name: {result.get('supplier_name_matched', 'No match')}")
        print(f"Matched party name: {result.get('party_name_matched', 'No match')}")
        
        # If queue mode is enabled, store in OCR queue
        if queue_mode:
            from .ocr_queue import OCRQueue
            queue = OCRQueue()
            entry = {
                "image": encoded_image,
                "ocr_data": result
            }
            entry_ids = queue.add_entries([entry])
            result["queue_entry_id"] = entry_ids[0]
            print("\n=== Queue Status ===")
            print(f"Added to queue with ID: {entry_ids[0]}")
    
        return result
    except Exception as e:
        print(f"Error in parse_register_entry: {str(e)}")
        raise DataError({"status": "error", "message": f"Error processing invoice: {str(e)}"})

# Keep the encode_image function at module level for backward compatibility
def encode_image(image_path: str) -> str:
    """Encode an image file to base64 string."""
    parser = InvoiceParser()
    return parser.encode_image(image_path)

# Example usage:
# encoded_image = encode_image("path/to/image.jpg")
# result = parse_register_entry(encoded_image)
# print(f"Parsed and matched result: {result}")
