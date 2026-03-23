"""MCP (Model Context Protocol) server for ingredient and product lookup tools."""
import json
from typing import Any, Dict, List, Optional
from .tools import ProductLookupTool, ChemicalDataTool
import logging

logger = logging.getLogger(__name__)


class IngredientIQMCPServer:
    """MCP Server exposing ingredient lookup and safety analysis tools."""
    
    def __init__(self):
        """Initialize MCP server with available tools."""
        self.tools = {
            "lookup_product": self._get_lookup_product_tool(),
            "search_ingredient": self._get_search_ingredient_tool(),
            "fetch_pubchem_data": self._get_fetch_pubchem_tool(),
            "fetch_ewg_rating": self._get_fetch_ewg_tool(),
        }
    
    def _get_lookup_product_tool(self) -> Dict[str, Any]:
        """Define lookup_product tool."""
        return {
            "name": "lookup_product",
            "description": "Search for a product by name and retrieve its ingredient list from Open Food Facts or Open Beauty Facts APIs.",
            "params": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Name of the product to search for (e.g., 'Neutrogena Ultra Sheer Sunscreen')",
                    }
                },
                "required": ["product_name"],
            },
            "handler": self._handle_lookup_product,
        }
    
    def _get_search_ingredient_tool(self) -> Dict[str, Any]:
        """Define search_ingredient tool."""
        return {
            "name": "search_ingredient",
            "description": "Search for information about a specific ingredient. Returns chemical properties, hazard data, and safety rating.",
            "params": {
                "type": "object",
                "properties": {
                    "ingredient_name": {
                        "type": "string",
                        "description": "Name of the ingredient to search for (e.g., 'sodium lauryl sulfate')",
                    }
                },
                "required": ["ingredient_name"],
            },
            "handler": self._handle_search_ingredient,
        }
    
    def _get_fetch_pubchem_tool(self) -> Dict[str, Any]:
        """Define fetch_pubchem_data tool."""
        return {
            "name": "fetch_pubchem_data",
            "description": "Retrieve detailed chemical data from PubChem including molecular formula, hazard flags, and regulatory information.",
            "params": {
                "type": "object",
                "properties": {
                    "chemical_name": {
                        "type": "string",
                        "description": "Chemical name to search for in PubChem",
                    }
                },
                "required": ["chemical_name"],
            },
            "handler": self._handle_fetch_pubchem,
        }
    
    def _get_fetch_ewg_tool(self) -> Dict[str, Any]:
        """Define fetch_ewg_rating tool."""
        return {
            "name": "fetch_ewg_rating",
            "description": "Fetch EWG Skin Deep safety score for a cosmetic ingredient (1-10 scale where 10 is most hazardous).",
            "params": {
                "type": "object",
                "properties": {
                    "ingredient_name": {
                        "type": "string",
                        "description": "Cosmetic ingredient name to look up on EWG Skin Deep",
                    }
                },
                "required": ["ingredient_name"],
            },
            "handler": self._handle_fetch_ewg,
        }
    
    def _handle_lookup_product(self, product_name: str) -> Dict[str, Any]:
        """Handle product lookup tool call."""
        try:
            result = ProductLookupTool.lookup_product(product_name)
            if result:
                return {
                    "success": True,
                    "data": result,
                }
            else:
                return {
                    "success": False,
                    "error": f"Product '{product_name}' not found in any database",
                }
        except Exception as e:
            logger.error(f"Error looking up product: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def _handle_search_ingredient(self, ingredient_name: str) -> Dict[str, Any]:
        """Handle ingredient search tool call."""
        try:
            # This would be used by RAG to search the KB
            # For now, placeholder that returns a structured response
            return {
                "success": True,
                "ingredient": ingredient_name,
                "message": "Ingredient search handled by RAG pipeline",
            }
        except Exception as e:
            logger.error(f"Error searching ingredient: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def _handle_fetch_pubchem(self, chemical_name: str) -> Dict[str, Any]:
        """Handle PubChem data fetch tool call."""
        try:
            result = ChemicalDataTool.search_pubchem(chemical_name)
            if result:
                return {
                    "success": True,
                    "data": result,
                }
            else:
                return {
                    "success": False,
                    "error": f"Chemical '{chemical_name}' not found in PubChem",
                }
        except Exception as e:
            logger.error(f"Error fetching PubChem data: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def _handle_fetch_ewg(self, ingredient_name: str) -> Dict[str, Any]:
        """Handle EWG rating fetch tool call."""
        try:
            # This would connect to EWG database
            # Placeholder for now
            return {
                "success": True,
                "ingredient": ingredient_name,
                "message": "EWG lookup would be implemented here",
            }
        except Exception as e:
            logger.error(f"Error fetching EWG rating: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def get_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available tools."""
        return {
            name: {
                "name": tool["name"],
                "description": tool["description"],
                "params": tool["params"],
            }
            for name, tool in self.tools.items()
        }
    
    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool with the given arguments.
        
        Args:
            tool_name: Name of the tool to call
            args: Tool arguments
            
        Returns:
            Tool result
        """
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found",
            }
        
        tool = self.tools[tool_name]
        handler = tool.get("handler")
        
        if not handler:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' has no handler",
            }
        
        try:
            return handler(**args)
        except TypeError as e:
            return {
                "success": False,
                "error": f"Invalid arguments for '{tool_name}': {str(e)}",
            }


# Global MCP server instance
mcp_server = IngredientIQMCPServer()
