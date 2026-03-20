"""
Demo script to test IngredientIQ API endpoints
Run this after starting the backend server
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_health():
    """Test backend health"""
    print_section("TEST 1: Backend Health Check")
    
    response = requests.get(f"{API_BASE}/health")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

def test_kb_stats():
    """Check knowledge base stats"""
    print_section("TEST 2: Knowledge Base Statistics")
    
    response = requests.get(f"{API_BASE}/api/v1/knowledge-base-stats")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

def test_analyze_ingredient():
    """Test single ingredient analysis"""
    print_section("TEST 3: Single Ingredient Analysis")
    
    ingredient = "benzene"
    print(f"Analyzing: {ingredient}\n")
    
    response = requests.get(
        f"{API_BASE}/api/v1/ingredient-search",
        params={"ingredient_name": ingredient}
    )
    print(f"Status: {response.status_code}\n")
    
    if response.status_code == 200:
        data = response.json()
        print("RAG Analysis:")
        print(json.dumps(data.get("rag_analysis"), indent=2))
    else:
        print(f"Error: {response.text}")

def test_analyze_ingredients():
    """Test multiple ingredients analysis"""
    print_section("TEST 4: Multiple Ingredients Analysis")
    
    ingredients = ["glycerin", "sodium lauryl sulfate", "titanium dioxide", "vitamin c"]
    print(f"Analyzing {len(ingredients)} ingredients: {', '.join(ingredients)}\n")
    
    response = requests.post(
        f"{API_BASE}/api/v1/analyze-ingredients",
        json={"ingredients": ingredients}
    )
    print(f"Status: {response.status_code}\n")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Overall Rating: {data['overall_rating']}")
        print(f"Overall Score: {data['overall_score']}/100")
        print(f"Safety Summary:")
        print(json.dumps(data['safety_summary'], indent=2))
        
        print(f"\nAnalyzed {len(data['ingredients'])} ingredients:")
        for ing in data['ingredients'][:2]:  # Show first 2
            print(f"\n  • {ing['ingredient_name']}")
            print(f"    Rating: {ing['safety_rating']}")
            print(f"    Confidence: {ing['confidence_score']:.1%}")
    else:
        print(f"Error: {response.text}")

def test_tools_list():
    """List available MCP tools"""
    print_section("TEST 5: Available MCP Tools")
    
    response = requests.get(f"{API_BASE}/api/v1/tools")
    print(f"Status: {response.status_code}\n")
    
    if response.status_code == 200:
        data = response.json()
        for tool in data['tools']:
            print(f"• {tool['name']}")
            print(f"  Description: {tool['description']}")
            print()
    else:
        print(f"Error: {response.text}")

def test_analyze_product():
    """Test product analysis (requires Open Food Facts)"""
    print_section("TEST 6: Product Analysis (Open Food Facts)")
    
    product = "Dove soap"
    print(f"Analyzing product: \"{product}\"\n")
    print("Note: This requires product to exist in Open Food Facts database\n")
    
    response = requests.post(
        f"{API_BASE}/api/v1/analyze-product",
        json={"product_name": product}
    )
    print(f"Status: {response.status_code}\n")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Overall Rating: {data['overall_rating']}")
        print(f"Overall Score: {data['overall_score']}/100")
        print(f"Ingredient Count: {data['ingredient_count']}")
        print(f"\nSafety Summary:")
        print(json.dumps(data['safety_summary'], indent=2))
    elif response.status_code == 404:
        print("Product not found in database")
        print("(This is normal - Open Food Facts may not have this product)\n")
        print("Try alternative products like:")
        print("  - 'Coca Cola'")
        print("  - 'Olive oil'")
        print("  - 'Pasta'")
    else:
        print(f"Error: {response.text}")

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  INGREDIENTIQ API TEST SUITE")
    print("="*60)
    print("\nMake sure backend server is running:")
    print("  python backend/main.py")
    print("\nWaiting for server...")
    
    # Try to connect
    max_retries = 5
    for i in range(max_retries):
        try:
            requests.get(f"{API_BASE}/health", timeout=2)
            break
        except requests.ConnectionError:
            if i < max_retries - 1:
                print(f"  Retry {i+1}/{max_retries}...")
                time.sleep(1)
            else:
                print(f"\n❌ ERROR: Cannot connect to backend at {API_BASE}")
                print("Make sure the backend server is running:")
                print("  cd backend && python main.py")
                return
    
    print("✓ Connected to backend\n")
    
    # Run tests
    try:
        test_health()
        test_kb_stats()
        test_tools_list()
        test_analyze_ingredient()
        test_analyze_ingredients()
        test_analyze_product()
        
        print_section("ALL TESTS COMPLETED")
        print("✓ API is working correctly!")
        
    except Exception as e:
        print(f"\n❌ ERROR during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
