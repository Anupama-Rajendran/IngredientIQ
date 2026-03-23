"""Hybrid product lookup strategy combining multiple sources with ranking."""
import asyncio
import time
from typing import Dict, List, Optional, Tuple
from fuzzywuzzy import fuzz
import re
import os
import json


class ProductMatcher:
    """Fuzzy matching for product names."""
    
    @staticmethod
    def extract_brand_and_type(product_name: str) -> Tuple[str, str]:
        """Extract brand and product type from product name.
        
        Example:
            "Aveeno daily moisturizing body wash"
            → brand="aveeno", type="body wash"
        """
        name_lower = product_name.lower()
        
        # Common product type keywords
        product_types = [
            'body wash', 'face wash', 'cleanser', 'moisturizer', 'sunscreen',
            'lotion', 'cream', 'serum', 'mist', 'spray', 'shampoo', 'conditioner',
            'toothpaste', 'deodorant', 'soap', 'gel', 'mask', 'oil', 'balm',
            'ketchup', 'sauce', 'chips', 'cola', 'soda', 'drink', 'juice'
        ]
        
        product_type = ""
        for ptype in product_types:
            if ptype in name_lower:
                product_type = ptype
                break
        
        # Extract brand (usually first word or words before type)
        brand = name_lower.split(product_type)[0].strip() if product_type else name_lower
        brand = brand.split()[0] if brand.split() else brand
        
        return brand, product_type
    
    @staticmethod
    def fuzzy_match_local(query: str, candidates: List[Dict]) -> List[Tuple[Dict, float]]:
        """Fuzzy match query against local candidates.
        
        Returns:
            List of (candidate, score) tuples sorted by score descending
        """
        results = []
        query_lower = query.lower()
        
        for candidate in candidates:
            # Match against product name
            name = candidate.get('name', '').lower()
            brand = candidate.get('brand', '').lower()
            
            # Calculate similarity scores
            name_score = fuzz.token_sort_ratio(query_lower, name)
            brand_score = fuzz.token_sort_ratio(query_lower, brand)
            
            # Use highest score, with name being primary
            combined_score = max(name_score * 0.7 + brand_score * 0.3, name_score)
            
            if combined_score > 50:  # Minimum threshold
                results.append((candidate, combined_score))
        
        # Sort by score descending
        return sorted(results, key=lambda x: x[1], reverse=True)


class ResultRanker:
    """Rank and compare results from multiple sources."""
    
    @staticmethod
    def calculate_relevance_score(product: Dict, query: str) -> float:
        """Calculate relevance score for a product (0.0-1.0).
        
        Factors:
        - Name match quality
        - Brand recognition
        - Data completeness (ingredients)
        - Source authority
        """
        score = 0.0
        query_lower = query.lower()
        
        # Name match (40%)
        name_match = fuzz.token_sort_ratio(query_lower, product.get('name', '').lower()) / 100.0
        score += name_match * 0.4
        
        # Brand consistency (20%)
        brand_in_query = any(word in query_lower for word in product.get('brand', '').lower().split())
        score += (0.2 if brand_in_query else 0.0)
        
        # Data completeness (20%)
        ingredients = product.get('ingredients', [])
        has_ingredients = 0.2 if ingredients and len(ingredients) > 0 else 0.0
        score += has_ingredients
        
        # Source authority (20%)
        source = product.get('source', '')
        source_scores = {
            'preseeded': 0.20,
            'cache': 0.15,
            'OpenBeautyFacts': 0.18,
            'OpenFoodFacts': 0.17,
            'INCIpedia': 0.19,
            'EWG': 0.20,
        }
        score += source_scores.get(source, 0.0)
        
        return min(score, 1.0)
    
    @staticmethod
    def rank_results(results: List[Dict], query: str) -> List[Dict]:
        """Rank multiple results and return sorted list.
        
        Returns:
            Sorted list with relevance_score added to each result
        """
        scored_results = []
        
        for result in results:
            if result:
                score = ResultRanker.calculate_relevance_score(result, query)
                result['relevance_score'] = score
                scored_results.append(result)
        
        # Sort by relevance score descending
        return sorted(scored_results, key=lambda x: x.get('relevance_score', 0), reverse=True)


class HybridProductLookup:
    """Hybrid product lookup combining multiple strategies."""
    
    def __init__(self, tools_module=None):
        """Initialize hybrid lookup with reference to tools module.
        
        Args:
            tools_module: Reference to mcp_server.tools for accessing
                         ProductDatabase, ProductCache, and APIs
        """
        self.tools = tools_module
        self.matcher = ProductMatcher()
        self.ranker = ResultRanker()
    
    async def lookup_product_hybrid(self, product_name: str, timeout: float = 8.0) -> Optional[Dict]:
        """Hybrid product lookup with fallback strategy.
        
        Flow:
        1. Check cache (instant)
        2. Check preseeded DB (instant)
        3. Fuzzy match preseeded DB (fast)
        4. Parallel API calls with timeout (slow but comprehensive)
        5. Rank and return best match
        
        Args:
            product_name: Product name to search for
            timeout: Total timeout in seconds
            
        Returns:
            Best matching product dict or None
        """
        if not product_name:
            return None
        
        print(f"\n[HybridLookup] Starting for: '{product_name}'")
        start_time = time.time()
        
        # Step 1: Check Cache (DISABLED - bypass cache to fetch fresh data)
        # print(f"[Step 1] Checking cache...")
        # if self.tools and hasattr(self.tools, 'ProductCache'):
        #     cache = self.tools.ProductCache()
        #     cached = cache.get(product_name)
        #     if cached:
        #         print(f"[Cache] ✓ HIT in {time.time() - start_time:.3f}s")
        #         return cached
        
        # Step 2: Check Preseeded Database + Fuzzy Match (instant)
        print(f"[Step 2] Checking preseeded database...")
        results = []
        
        if self.tools and hasattr(self.tools, 'ProductDatabase'):
            db = self.tools.ProductDatabase()
            
            # Try exact match
            exact_match = db.lookup(product_name)
            if exact_match:
                print(f"[Preseeded] ✓ Exact match in {time.time() - start_time:.3f}s")
                self._cache_if_needed(product_name, exact_match)
                return exact_match
            
            # Try fuzzy match on preseeded DB
            preseeded_list = list(db.products.values())
            fuzzy_matches = self.matcher.fuzzy_match_local(product_name, preseeded_list)
            
            if fuzzy_matches and fuzzy_matches[0][1] > 75:  # High confidence threshold
                best_match = fuzzy_matches[0][0]
                print(f"[Preseeded] ✓ Fuzzy match ({fuzzy_matches[0][1]:.0f}%) in {time.time() - start_time:.3f}s")
                self._cache_if_needed(product_name, best_match)
                return best_match
            
            # Add fuzzy matches to results list for later ranking
            for match, score in fuzzy_matches[:3]:  # Top 3 fuzzy matches
                match_copy = match.copy()
                match_copy['fuzzy_score'] = score
                results.append(match_copy)
        
        # Step 3: Parallel API calls (with timeout)
        print(f"[Step 3] Parallel API calls...")
        remaining_time = timeout - (time.time() - start_time)
        
        if remaining_time > 1.0 and self.tools:
            api_results = await self._parallel_api_calls(product_name, remaining_time)
            results.extend(api_results)
        
        # Step 4: Rank Results
        print(f"[Step 4] Ranking results...")
        if results:
            ranked = self.ranker.rank_results(results, product_name)
            
            if ranked and ranked[0].get('relevance_score', 0) > 0.5:
                best = ranked[0]
                print(f"[Ranking] ✓ Best match: {best.get('name')} (score: {best.get('relevance_score'):.2f})")
                self._cache_if_needed(product_name, best)
                return best
        
        # Step 5: Not Found
        print(f"[HybridLookup] ✗ Product not found in {time.time() - start_time:.3f}s")
        return None
    
    async def _parallel_api_calls(self, product_name: str, timeout: float) -> List[Dict]:
        """Make parallel API calls with timeout.
        
        Queries:
        - OpenBeautyFacts (if cosmetics detected)
        - OpenFoodFacts (always)
        
        Returns:
            List of successful API results
        """
        results = []
        
        # Detect if cosmetic
        is_cosmetic = self._detect_cosmetic(product_name)
        
        tasks = []
        
        if is_cosmetic:
            tasks.append(self._call_openbeautyfacts_async(product_name))
        
        tasks.append(self._call_openfoodfacts_async(product_name))
        
        try:
            # Run all tasks in parallel with timeout
            api_results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
            
            # Filter out None and exceptions
            for result in api_results:
                if isinstance(result, dict) and result:
                    results.append(result)
        
        except asyncio.TimeoutError:
            print(f"[API] ✗ Timeout after {timeout}s")
        
        return results
    
    async def _call_openbeautyfacts_async(self, product_name: str) -> Optional[Dict]:
        """Async wrapper for OpenBeautyFacts API call."""
        try:
            if self.tools and hasattr(self.tools, 'ProductLookupTool'):
                # Run the synchronous call in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self.tools.ProductLookupTool._lookup_beauty_facts,
                    product_name
                )
                return result
        except Exception as e:
            print(f"[OpenBeautyFacts] Error: {e}")
        
        return None
    
    async def _call_openfoodfacts_async(self, product_name: str) -> Optional[Dict]:
        """Async wrapper for OpenFoodFacts API call."""
        try:
            if self.tools and hasattr(self.tools, 'ProductLookupTool'):
                # Run the synchronous call in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self.tools.ProductLookupTool._lookup_food_facts,
                    product_name
                )
                return result
        except Exception as e:
            print(f"[OpenFoodFacts] Error: {e}")
        
        return None
    
    def _detect_cosmetic(self, product_name: str) -> bool:
        """Detect if product is cosmetic/skincare."""
        cosmetics_keywords = {
            'cream', 'lotion', 'serum', 'moisturizer', 'sunscreen', 'cleanser',
            'mask', 'oil', 'gel', 'balm', 'shampoo', 'conditioner', 'soap',
            'deodorant', 'perfume', 'cologne', 'toner', 'essence', 'treatment',
            'makeup', 'cosmetic', 'skincare', 'face', 'body', 'hair', 'beauty'
        }
        return any(keyword in product_name.lower() for keyword in cosmetics_keywords)
    
    def _cache_if_needed(self, product_name: str, product_data: Dict):
        """Cache product result if not already cached."""
        try:
            if self.tools and hasattr(self.tools, 'ProductCache'):
                cache = self.tools.ProductCache()
                # Only cache if from external source (not preseeded)
                if product_data.get('source') != 'preseeded':
                    cache.set(product_name, product_data)
        except Exception as e:
            print(f"[Cache] Error caching: {e}")


# Async wrapper for integration with FastAPI
async def hybrid_lookup_product(product_name: str, tools_module=None) -> Optional[Dict]:
    """Async entry point for hybrid product lookup.
    
    Args:
        product_name: Product name to search
        tools_module: Reference to tools module (optional)
        
    Returns:
        Product dict with ingredients or None
    """
    lookup = HybridProductLookup(tools_module)
    return await lookup.lookup_product_hybrid(product_name)
