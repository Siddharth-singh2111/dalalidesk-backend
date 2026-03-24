import os
from typing import List, Optional, Tuple, Dict
from rapidfuzz import process, distance
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

from API_Database import retrieve_indivijual
from .name_cache import NameMatchCache

load_dotenv()

class NameMatcher:
    """A class to match business names using fuzzy matching and LLM verification."""
    
    def __init__(self, cache_dir: str = "data"):
        """Initialize the name matcher with LLM and cache.
        
        Args:
            cache_dir: Directory to store the cache file
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # Using 3.5 for cost efficiency
            api_key=api_key,
            temperature=0
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert in Indian business names and common variations."),
            ("user", """Query name: '{query}'
            Potential matches: {candidates}
            
            If one of the potential matches is clearly the same business (considering common variations, typos, or abbreviations), return that name.
            If none of the matches seem to be the same business, return 'None'.
            If you find a match, you MUST return the EXACT string from the potential matches list.
            Response format: single line with match or 'None'""")
        ])
        
        # Initialize cache
        cache_file = os.path.join(cache_dir, "name_match_cache.json")
        self.cache = NameMatchCache(cache_file)

    def get_fuzzy_matches(self, query: str, database_names: List[str], limit: int = 10) -> List[Tuple[str, float]]:
        """Get initial matches using fuzzy matching.
        
        Args:
            query: The name to match against the database
            database_names: List of names from the database
            limit: Maximum number of matches to return
            
        Returns:
            List of tuples containing (name, score)
        """
        # Convert query to lowercase
        query = query.lower()
        
        # Convert all database names to lowercase for comparison
        lowercase_names = [name.lower() for name in database_names]
        
        # Get matches using lowercase versions
        matches = process.extract(
            query, 
            lowercase_names, 
            scorer=distance.JaroWinkler.distance, 
            limit=limit
        )
        
        # Map back to original case names
        original_case_matches = [
            (database_names[lowercase_names.index(match[0])], match[1]) 
            for match in matches
        ]
        
        # Debug output
        print("\n=== Top Fuzzy Matches ===")
        print(f"Query: {query}")
        for name, score in original_case_matches:
            print(f"Match: {name}, Score: {score}")
        
        return original_case_matches

    def verify_match(self, query: str, candidates: List[str]) -> Optional[str]:
        """Verify the best match using LLM.
        
        Args:
            query: The original query name
            candidates: List of potential matches
            
        Returns:
            The verified match or None if no confident match found
        """
        # Check cache first
        cached_result = self.cache.get(query)

        if cached_result:
            return cached_result
            
        # Try exact match first (case-insensitive)
        for candidate in candidates:
            if query.lower() == candidate.lower():
                self.cache.set(query, candidate)
                return candidate
            
        try:
            messages = self.prompt.format_messages(
                query=query,
                candidates=", ".join(candidates)
            )
            
            # Debug output before AI call
            print("\n=== AI Verification ===")
            print(f"Query sent to AI: {query}")
            print(f"Candidates sent to AI: {candidates}")
            
            response = self.llm.invoke(messages)
            result = response.content.strip()
            
            # Debug output after AI response
            print(f"AI response: {result}")
            
            # If we found a valid match, cache it
            if result in candidates:
                self.cache.set(query, result)
                return result
            return None
            
        except Exception as e:
            print(f"Error in LLM verification: {str(e)}")
            return None

    def find_match(self, query: str, entity_type: str = 'supplier') -> Optional[str]:
        """Find the best match for a query name in the database.
        
        Args:
            query: The name to match
            entity_type: Type of entity to match against ('supplier' or 'party')
            
        Returns:
            The best matching name or None if no confident match found
        """
        try:
            # Check cache first
            cached_result = self.cache.get(query)
            
            if cached_result:
                return cached_result
            
            # Get all names from database
            data = retrieve_indivijual.get_all_names_ids(entity_type, dict_cursor=False)
            database_names = [y[1] for y in data]
            
            # Get fuzzy matches
            matches = self.get_fuzzy_matches(query, database_names)
            if not matches:
                return None
                
            # Extract just the names from matches
            candidate_names = [match[0] for match in matches]
            
            # Verify using LLM
            result = self.verify_match(query, candidate_names)
            
            # Cache the result if we found a match
            if result:
                self.cache.set(query, result)
                
            return result
            
        except Exception as e:
            print(f"Error in name matching: {str(e)}")
            return None

    def get_cache_stats(self) -> Dict[str, float]:
        """Get cache performance statistics."""
        return self.cache.get_stats()

# Example usage:
# matcher = NameMatcher()
# result = matcher.find_match("rachit fashion", "supplier")
# print(f"Match found: {result}")
# print(f"Cache stats: {matcher.get_cache_stats()}")
