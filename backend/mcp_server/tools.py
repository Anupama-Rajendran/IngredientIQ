"""MCP tools for product lookup and chemical data retrieval."""
import requests
import json
from typing import Dict, List, Optional, Tuple
import re
from config import settings
import sqlite3
import time
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed


# Try to import fuzzywuzzy for fuzzy matching
try:
    from fuzzywuzzy import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    print("[WARNING] fuzzywuzzy not installed. Fuzzy matching disabled.")


class ProductCache:
    """Simple SQLite cache for product lookups."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Get path relative to tools.py file
            module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(module_dir, "data", "products_cache.db")
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize cache database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products_cache (
                    product_name TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Cache] Error initializing database: {e}")
    
    def get(self, product_name: str) -> Optional[Dict]:
        """Retrieve cached product data."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data FROM products_cache WHERE product_name = ?",
                (product_name.lower(),)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                print(f"[Cache] Hit for '{product_name}'")
                return json.loads(result[0])
        except Exception as e:
            print(f"[Cache] Error reading: {e}")
        
        return None
    
    def set(self, product_name: str, data: Dict) -> bool:
        """Store product data in cache."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO products_cache (product_name, data) VALUES (?, ?)",
                (product_name.lower(), json.dumps(data))
            )
            conn.commit()
            conn.close()
            print(f"[Cache] Stored '{product_name}'")
            return True
        except Exception as e:
            print(f"[Cache] Error writing: {e}")
        
        return False


class ProductDatabase:
    """Load preseeded products from local JSON."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Get path relative to this tools.py file
            module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(module_dir, "data", "products_database.json")
        self.db_path = db_path
        self.products = self._load_db()
    
    def _load_db(self) -> Dict:
        """Load preseeded products."""
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    count = len(data.get('products', {}))
                    print(f"[Database] Loaded {count} preseeded products")
                    return data.get('products', {})
        except Exception as e:
            print(f"[Database] Error loading: {e}")
        
        return {}
    
    def lookup(self, product_name: str) -> Optional[Dict]:
        """Search preseeded database."""
        if not product_name:
            return None
        
        # Exact match first
        key = product_name.lower()
        if key in self.products:
            print(f"[Database] Found exact match: {product_name}")
            return self.products[key]
        
        # Fuzzy match on keywords
        search_terms = set(product_name.lower().split())
        for db_name, product_data in self.products.items():
            db_terms = set(db_name.split())
            if search_terms & db_terms:  # Check overlap
                print(f"[Database] Found fuzzy match: {db_name} for '{product_name}'")
                return product_data
        
        return None


class FuzzyProductMatcher:
    """Fuzzy matching for product names and fuzzy lookup in database."""
    
    @staticmethod
    def fuzzy_match_products(product_name: str, database: Dict[str, Dict], threshold: int = 70) -> List[Tuple[str, Dict, int]]:
        """Find fuzzy matches in preseeded database.
        
        Args:
            product_name: Product name to search for
            database: Dictionary of preseeded products
            threshold: Minimum match score (0-100)
            
        Returns:
            List of (key, product_data, score) tuples, sorted by score descending
        """
        if not FUZZY_AVAILABLE or not database:
            return []
        
        matches = []
        product_lower = product_name.lower()
        
        for db_key, product_data in database.items():
            # Score the key directly
            key_score = fuzz.ratio(product_lower, db_key)
            
            # Also score against product name if available
            product_full_name = product_data.get('name', '').lower()
            name_score = fuzz.ratio(product_lower, product_full_name)
            
            # Score against brand + product keywords
            brand = product_data.get('brand', '').lower()
            brand_score = fuzz.ratio(product_lower, brand) if brand else 0
            
            # Take the highest score
            best_score = max(key_score, name_score, brand_score)
            
            if best_score >= threshold:
                matches.append((db_key, product_data, best_score))
                print(f"[Fuzzy] Match '{db_key}': {best_score}% confidence")
        
        # Sort by score descending
        matches.sort(key=lambda x: x[2], reverse=True)
        return matches
    
    @staticmethod
    def extract_product_keywords(product_name: str) -> Dict[str, str]:
        """Extract brand and product type from product name.
        
        Args:
            product_name: Full product name (e.g., "Aveeno Daily Moisturizing Body Wash")
            
        Returns:
            {"brand": "aveeno", "type": "body wash", "full": "aveeno daily moisturizing body wash"}
        """
        product_lower = product_name.lower()
        
        # Common product keywords
        product_types = [
            'body wash', 'face wash', 'cleanser', 'moisturizer', 'lotion', 'cream',
            'sunscreen', 'shampoo', 'conditioner', 'toothpaste', 'soap',
            'serum', 'mask', 'oil', 'gel', 'balm', 'spray', 'powder'
        ]
        
        # Extract type
        detected_type = None
        for ptype in product_types:
            if ptype in product_lower:
                detected_type = ptype
                break
        
        # Extract brand (first word usually)
        words = product_name.split()
        brand = words[0].lower() if words else ""
        
        return {
            "brand": brand,
            "type": detected_type or "product",
            "full": product_lower
        }


class ResultRanker:
    """Rank and filter lookup results from multiple sources."""
    
    @staticmethod
    def rank_results(results: List[Dict], original_query: str) -> List[Dict]:
        """Rank results by relevance, confidence, and source quality.
        
        Args:
            results: List of product results from various sources
            original_query: Original user query
            
        Returns:
            Sorted list of results with confidence scores
        """
        if not results:
            return []
        
        # Score each result
        scored_results = []
        for result in results:
            score = ResultRanker._calculate_confidence(result, original_query)
            result['confidence_score'] = score
            scored_results.append(result)
        
        # Sort by confidence score
        scored_results.sort(key=lambda x: x.get('confidence_score', 0), reverse=True)
        return scored_results
    
    @staticmethod
    def _calculate_confidence(result: Dict, query: str) -> float:
        """Calculate confidence score for a single result (0.0 - 1.0).
        
        Factors:
        - Source authority (preseeded > cache > API)
        - Name similarity
        - Has ingredients
        """
        score = 0.5  # Base score
        
        # Source bonus
        source = result.get('source', 'unknown').lower()
        if source == 'preseeded':
            score += 0.3
        elif source == 'cache':
            score += 0.2
        elif source in ['openfoodfacts', 'openbeautyfacts']:
            score += 0.1
        
        # Has ingredients bonus
        ingredients = result.get('ingredients', [])
        if ingredients and len(ingredients) > 0:
            score += 0.1
        
        # Name similarity bonus (if fuzzy matching available)
        if FUZZY_AVAILABLE:
            result_name = result.get('name', '').lower()
            query_lower = query.lower()
            similarity = fuzz.ratio(query_lower, result_name) / 100.0
            score += similarity * 0.2  # Up to +0.2 for perfect match
        
        return min(score, 1.0)  # Cap at 1.0


class ProductLookupTool:
    """Tool for looking up product ingredients from multiple sources."""
    
    # Initialize cache and database at module level
    _cache = ProductCache()
    _database = ProductDatabase()
    
    COSMETICS_KEYWORDS = {
        'cream', 'lotion', 'serum', 'moisturizer', 'sunscreen', 'cleanser',
        'mask', 'oil', 'gel', 'balm', 'shampoo', 'conditioner', 'soap',
        'deodorant', 'perfume', 'cologne', 'toner', 'essence', 'treatment',
        'concealer', 'foundation', 'powder', 'blush', 'lipstick', 'mascara',
        'eyeshadow', 'liner', 'primer', 'highlighter', 'bronzer', 'contour',
        'mist', 'spray', 'wax', 'pomade', 'styling', 'paste', 'scrub',
        'exfoliant', 'peel', 'body wash', 'body lotion', 'face wash',
        'acne', 'anti-aging', 'retinol', 'vitamin c', 'hyaluronic', 'collagen',
        'skincare', 'facial', 'beauty', 'cosmetic', 'toothpaste', 'lip balm'
    }
    
    @staticmethod
    def is_cosmetic_product(product_name: str) -> bool:
        """Detect if product is cosmetic/skincare related."""
        product_lower = product_name.lower()
        return any(keyword in product_lower for keyword in ProductLookupTool.COSMETICS_KEYWORDS)
    
    @staticmethod
    def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 0.5):
        """Retry function with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return func()
            except requests.Timeout:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"[Retry] Attempt {attempt + 1}/{max_retries}, waiting {delay}s...")
                    time.sleep(delay)
                else:
                    print(f"[Retry] Failed after {max_retries} attempts")
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"[Retry] Error (attempt {attempt + 1}): {e}, waiting {delay}s...")
                    time.sleep(delay)
                else:
                    raise
    
    @staticmethod
    def lookup_product(product_name: str) -> Optional[Dict]:
        """Look up a product by name and get ingredients.
        
        Hybrid strategy:
        1. Cache (< 1ms) - instant
        2. Preseeded database (< 6ms) - instant
        3. Fuzzy match preseeded DB (< 50ms) - fast
        4. External APIs with retry logic (3-10s) - comprehensive
        5. Rank and return best match
        """
        if not product_name:
            return None
        
        print(f"\n[HybridLookup] Starting product lookup: '{product_name}'")
        start_time = time.time()
        
        # Step 1: Check cache
        print(f"[Step 1] Checking cache...")
        cached = ProductLookupTool._cache.get(product_name)
        if cached:
            print(f"[Cache] [OK] HIT in {time.time() - start_time:.3f}s")
            return cached
        
        # Step 2: Check preseeded database (exact match)
        print(f"[Step 2] Checking preseeded database (exact match)...")
        db_product = ProductLookupTool._database.lookup(product_name)
        if db_product:
            product = {
                "name": db_product.get('name', 'Unknown'),
                "brand": db_product.get('brand', 'Unknown'),
                "ingredients": db_product.get('ingredients', []),
                "source": db_product.get('source', 'preseeded')
            }
            print(f"[Preseeded] [OK] Exact match in {time.time() - start_time:.3f}s")
            ProductLookupTool._cache.set(product_name, product)
            return product
        
        # Step 3: Fuzzy match preseeded database
        print(f"[Step 3] Fuzzy matching preseeded database...")
        if FUZZY_AVAILABLE and ProductLookupTool._database.products:
            fuzzy_matches = FuzzyProductMatcher.fuzzy_match_products(
                product_name,
                ProductLookupTool._database.products,
                threshold=70
            )
            
            if fuzzy_matches:
                best_match = fuzzy_matches[0][1]  # Get product data
                score = fuzzy_matches[0][2]  # Get score
                
                if score > 80:  # High confidence threshold
                    product = {
                        "name": best_match.get('name', 'Unknown'),
                        "brand": best_match.get('brand', 'Unknown'),
                        "ingredients": best_match.get('ingredients', []),
                        "source": best_match.get('source', 'preseeded'),
                        "fuzzy_match_score": score
                    }
                    print(f"[Fuzzy] [OK] High confidence match ({score}%) in {time.time() - start_time:.3f}s")
                    ProductLookupTool._cache.set(product_name, product)
                    return product
                elif score > 70:
                    # Medium confidence - log but continue to API
                    print(f"[Fuzzy] Medium confidence match ({score}%), checking APIs...")
        
        # Step 4: Try external APIs with retry logic
        print(f"[Step 4] Parallel API calls...")
        api_results = []
        
        try:
            is_cosmetic = ProductLookupTool.is_cosmetic_product(product_name)
            
            if is_cosmetic:
                print(f"[Lookup] Detected as cosmetic product, trying OpenBeautyFacts...")
                result = ProductLookupTool._lookup_beauty_facts(product_name)
                if result:
                    api_results.append(result)
            
            print(f"[Lookup] Trying OpenFoodFacts...")
            result = ProductLookupTool._lookup_food_facts(product_name)
            if result:
                api_results.append(result)
        
        except Exception as e:
            print(f"[Lookup] External API error: {e}")
        
        # Step 5: Rank and return best match
        print(f"[Step 5] Ranking results...")
        
        if api_results:
            # Return first successful API result (already searched by API quality order)
            best = api_results[0]
            if best:
                print(f"[API] [OK] Found via {best.get('source')} in {time.time() - start_time:.3f}s")
                ProductLookupTool._cache.set(product_name, best)
                return best
        
        print(f"[HybridLookup] ✗ Product not found in {time.time() - start_time:.3f}s")
        return None
    
    @staticmethod
    def _lookup_beauty_facts(product_name: str) -> Optional[Dict]:
        """Query OpenBeautyFacts API with retry logic and multiple search strategies."""
        try:
            # Try multiple search variations
            search_variations = [
                product_name,  # Original
                product_name.split()[0],  # First word only (e.g., "Aveeno")
                " ".join(product_name.split()[:2]),  # First two words
            ]
            
            for search_term in search_variations:
                if not search_term or len(search_term) < 2:
                    continue
                
                print(f"[OpenBeautyFacts] Trying: '{search_term}'")
                
                def api_call():
                    search_url = "https://world.openbeautyfacts.org/cgi/search.pl"
                    params = {
                        "search_terms": search_term,
                        "json": 1,
                        "page_size": 3  # Get top 3 to find best match
                    }
                    response = requests.get(search_url, params=params, timeout=5)  # Increased timeout
                    return response
                
                try:
                    response = ProductLookupTool.retry_with_backoff(api_call, max_retries=2, base_delay=0.5)
                except Exception as api_err:
                    print(f"[OpenBeautyFacts] API call failed for '{search_term}': {api_err}")
                    continue
                
                if response and response.status_code == 200:
                    data = response.json()
                    products = data.get('products', [])
                    
                    if products:
                        # Try to find product with ingredients
                        for product_data in products:
                            product = {
                                "name": product_data.get('product_name', 'Unknown'),
                                "brand": product_data.get('brands', 'Unknown'),
                                "ingredients": [],
                                "source": "OpenBeautyFacts"
                            }
                            
                            # Extract ingredients
                            if 'ingredients' in product_data and isinstance(product_data['ingredients'], list):
                                for ing in product_data['ingredients']:
                                    ing_text = ing.get('text', '') if isinstance(ing, dict) else str(ing)
                                    if ing_text:
                                        product['ingredients'].append(ing_text)
                            elif 'ingredients_text' in product_data:
                                ingredients_text = product_data['ingredients_text']
                                product['ingredients'] = [
                                    ing.strip() for ing in ingredients_text.split(',')
                                    if ing.strip()
                                ]
                            
                            # Return if we found ingredients or product name matches
                            if product['ingredients'] or (product_data.get('product_name') and len(product_data.get('product_name', '')) > 3):
                                print(f"[OpenBeautyFacts] Found: {product['name']} with {len(product['ingredients'])} ingredients")
                                return product
                    else:
                        print(f"[OpenBeautyFacts] No products returned for '{search_term}'")
                else:
                    print(f"[OpenBeautyFacts] HTTP {response.status_code if response else 'None'} for '{search_term}'")
                    
        except requests.Timeout:
            print(f"[OpenBeautyFacts] Timeout on search")
        except Exception as e:
            print(f"[OpenBeautyFacts] Unexpected error: {type(e).__name__}: {e}")
        
        return None
    
    @staticmethod
    def _lookup_food_facts(product_name: str) -> Optional[Dict]:
        """Query OpenFoodFacts API with retry logic and multiple search strategies."""
        try:
            # Try multiple search variations
            search_variations = [
                product_name,  # Original
                product_name.split()[0],  # First word (e.g., "Coca" from "Coca Cola")
                " ".join(product_name.split()[:2]),  # First two words
            ]
            
            for search_term in search_variations:
                if not search_term or len(search_term) < 2:
                    continue
                
                print(f"[OpenFoodFacts] Trying: '{search_term}'")
                
                def api_call():
                    search_url = "https://world.openfoodfacts.org/cgi/search.pl"
                    params = {
                        "search_terms": search_term,
                        "json": 1,
                        "page_size": 3  # Get top 3 to find best match
                    }
                    response = requests.get(search_url, params=params, timeout=5)  # Increased timeout
                    return response
                
                try:
                    response = ProductLookupTool.retry_with_backoff(api_call, max_retries=2, base_delay=0.5)
                except Exception as api_err:
                    print(f"[OpenFoodFacts] API call failed: {api_err}")
                    continue
                
                if response and response.status_code == 200:
                    data = response.json()
                    products = data.get('products', [])
                    
                    if products:
                        # Try to find product with ingredients
                        for product_data in products:
                            product = {
                                "name": product_data.get('product_name', 'Unknown'),
                                "brand": product_data.get('brands', 'Unknown'),
                                "ingredients": [],
                                "source": "OpenFoodFacts"
                            }
                            
                            # Extract ingredients
                            if 'ingredients' in product_data and isinstance(product_data['ingredients'], list):
                                for ing in product_data['ingredients']:
                                    ing_text = ing.get('text', '') if isinstance(ing, dict) else str(ing)
                                    if ing_text:
                                        product['ingredients'].append(ing_text)
                            elif 'ingredients_text' in product_data:
                                ingredients_text = product_data['ingredients_text']
                                product['ingredients'] = [
                                    ing.strip() for ing in ingredients_text.split(',')
                                    if ing.strip()
                                ]
                            
                            # Return if we found ingredients or product name matches
                            if product['ingredients'] or (product_data.get('product_name') and len(product_data.get('product_name', '')) > 3):
                                print(f"[OpenFoodFacts] Found: {product['name']} with {len(product['ingredients'])} ingredients")
                                return product
                    
        except requests.Timeout:
            print(f"[OpenFoodFacts] Timeout on search")
        except Exception as e:
            print(f"[OpenFoodFacts] Error: {e}")
        
        return None


class ChemicalDataTool:
    """Tool for retrieving chemical data from PubChem."""
    
    @staticmethod
    def search_pubchem(chemical_name: str) -> Optional[Dict]:
        """Search for chemical data in PubChem.
        
        Args:
            chemical_name: Name of chemical to search
            
        Returns:
            Dictionary with chemical data and properties
        """
        try:
            # Search for compound
            search_url = f"{settings.PUBCHEM_API}/compound/name/{chemical_name}/JSON"
            response = requests.get(search_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                compounds = data.get('PC_Compounds', [])
                
                if compounds:
                    compound = compounds[0]
                    
                    chem_data = {
                        "name": chemical_name,
                        "cas_number": None,
                        "molecular_formula": None,
                        "hazards": [],
                        "source": "PubChem"
                    }
                    
                    # Extract properties
                    props = compound.get('props', [])
                    for prop in props:
                        prop_name = prop.get('urn', {}).get('label', '')
                        prop_value = prop.get('value', {})
                        
                        if prop_name == 'Molecular Formula':
                            chem_data['molecular_formula'] = str(prop_value.get('sval', ''))
                        elif prop_name == 'IUPAC CAS':
                            chem_data['cas_number'] = str(prop_value.get('sval', ''))
                    
                    # Try to get GHS hazards
                    try:
                        hazard_url = f"{settings.PUBCHEM_API}/compound/name/{chemical_name}/property/GHSPictograms,GHSSignals,GHSHazardStatements/JSON"
                        hazard_response = requests.get(hazard_url, timeout=10)
                        if hazard_response.status_code == 200:
                            hazard_data = hazard_response.json()
                            # Extract hazard information if available
                    except:
                        pass
                    
                    return chem_data
            
        except Exception as e:
            print(f"Error searching PubChem: {e}")
        
        return None
    
    @staticmethod
    def parse_ingredients(ingredient_string: str) -> List[str]:
        """Parse a comma or semicolon-separated ingredient list.
        
        Args:
            ingredient_string: Raw ingredient string from label
            
        Returns:
            List of individual ingredient names
        """
        # Split by common delimiters
        ingredients = re.split(r'[,;]|\s+and\s+', ingredient_string)
        
        # Clean up each ingredient
        cleaned = []
        for ing in ingredients:
            ing = ing.strip().lower()
            # Remove common non-ingredient text
            ing = re.sub(r'\(.*?\)', '', ing).strip()
            if ing and len(ing) > 2:
                cleaned.append(ing)
        
        return cleaned


class EWGLookupTool:
    """Tool for looking up ingredients in EWG Skin Deep database."""
    
    @staticmethod
    def get_ewg_rating(ingredient_name: str) -> Optional[Dict]:
        """Get EWG Skin Deep rating for an ingredient.
        
        Args:
            ingredient_name: Name of ingredient
            
        Returns:
            Dictionary with EWG rating and hazard info
        """
        try:
            # Note: EWG doesn't have a free public API, so this is a placeholder
            # In production, you would either:
            # 1. Scrape the EWG website (with permission)
            # 2. Use a paid API service
            # 3. Maintain a local copy of the data
            
            # For now, return a note about the limitation
            return {
                "ingredient": ingredient_name,
                "rating": None,
                "note": "EWG data would require web scraping or paid API access",
                "source": "EWG Skin Deep"
            }
        except Exception as e:
            print(f"Error getting EWG rating: {e}")
        
        return None


class IngredientParserTool:
    """Tool for extracting and parsing ingredients from text."""
    
    @staticmethod
    def extract_ingredients_from_text(text: str) -> List[str]:
        """Extract ingredients from unstructured text.
        
        Args:
            text: Raw text potentially containing ingredients
            
        Returns:
            List of extracted ingredient names
        """
        # Look for common phrases indicating ingredient lists
        patterns = [
            r'ingredients?:?\s*([^.]+?)(?:contains?|free from|allergens?|warning)',
            r'contains?:?\s*([^.]+)',
            r'ingredient list:?\s*([^.]+)',
        ]
        
        ingredients = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                ingredient_text = match.group(1)
                parsed = ChemicalDataTool.parse_ingredients(ingredient_text)
                ingredients.extend(parsed)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_ingredients = []
        for ing in ingredients:
            if ing not in seen:
                seen.add(ing)
                unique_ingredients.append(ing)
        
        return unique_ingredients


class MCPToolRegistry:
    """Registry of available MCP tools."""
    
    TOOLS = {
        "lookup_product": {
            "description": "Look up a product by name and retrieve its ingredient list",
            "function": ProductLookupTool.lookup_product,
            "params": {
                "product_name": "str - Name of the product"
            }
        },
        "search_pubchem": {
            "description": "Search for chemical data in PubChem database",
            "function": ChemicalDataTool.search_pubchem,
            "params": {
                "chemical_name": "str - Name of the chemical"
            }
        },
        "parse_ingredients": {
            "description": "Parse a comma or semicolon-separated ingredient list",
            "function": ChemicalDataTool.parse_ingredients,
            "params": {
                "ingredient_string": "str - Raw ingredient string from label"
            }
        },
        "get_ewg_rating": {
            "description": "Get EWG Skin Deep safety rating for an ingredient",
            "function": EWGLookupTool.get_ewg_rating,
            "params": {
                "ingredient_name": "str - Name of ingredient"
            }
        },
        "extract_ingredients_from_text": {
            "description": "Extract ingredients from unstructured text (e.g., OCR output)",
            "function": IngredientParserTool.extract_ingredients_from_text,
            "params": {
                "text": "str - Raw text potentially containing ingredients"
            }
        }
    }
    
    @classmethod
    def get_tool(cls, tool_name: str):
        """Get a tool by name."""
        return cls.TOOLS.get(tool_name)
    
    @classmethod
    def list_tools(cls):
        """List all available tools."""
        return list(cls.TOOLS.keys())
