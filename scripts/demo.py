#!/usr/bin/env python3
"""
SearchIt Demo Script
Demonstrates the hybrid search and RAG capabilities
"""

import asyncio
import json
import requests
import time
from typing import Dict, Any, List

# Demo queries
SEARCH_QUERIES = [
    "What is machine learning?",
    "How do neural networks work?", 
    "What are the types of machine learning?",
    "What is deep learning?",
    "How does computer vision work?",
    "What is natural language processing?",
    "What programming language is best for AI?",
    "How do you evaluate machine learning models?",
    "What is big data?",
    "What are the ethical issues in AI?"
]

ASK_QUERIES = [
    "What are the main types of machine learning and how do they differ?",
    "How do convolutional neural networks work for image processing?",
    "What are the key components of a data science workflow?",
    "What ethical considerations should be taken when developing AI systems?",
    "How does reinforcement learning differ from supervised learning?"
]

GATEWAY_URL = "http://localhost:8000"

class SearchItDemo:
    """Demo client for SearchIt"""
    
    def __init__(self, gateway_url: str = GATEWAY_URL):
        self.gateway_url = gateway_url
        self.session = requests.Session()
    
    def check_health(self) -> bool:
        """Check if the gateway is healthy"""
        try:
            response = self.session.get(f"{self.gateway_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Perform a search query"""
        try:
            params = {
                "q": query,
                "top_k": top_k,
                "with_highlights": True
            }
            
            response = self.session.get(f"{self.gateway_url}/search", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def ask(self, question: str, top_k: int = 8) -> Dict[str, Any]:
        """Ask a question and get a grounded answer"""
        try:
            payload = {
                "question": question,
                "top_k": top_k,
                "ground": True
            }
            
            response = self.session.post(f"{self.gateway_url}/ask", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def submit_feedback(self, query: str, doc_id: str, chunk_id: str, label: str) -> Dict[str, Any]:
        """Submit feedback"""
        try:
            payload = {
                "query": query,
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "label": label,
                "user_id": "demo_user"
            }
            
            response = self.session.post(f"{self.gateway_url}/feedback", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def run_search_demo(self) -> None:
        """Run search demo"""
        print("\n" + "="*60)
        print("🔍 SEARCH DEMO")
        print("="*60)
        
        for i, query in enumerate(SEARCH_QUERIES[:3], 1):  # Show first 3 queries
            print(f"\n{i}. Query: {query}")
            print("-" * 50)
            
            start_time = time.time()
            result = self.search(query, top_k=3)
            search_time = time.time() - start_time
            
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                continue
            
            print(f"⏱️  Search time: {search_time:.2f}s")
            print(f"📊 Results: {len(result.get('results', []))} documents")
            
            # Show top results
            for j, doc in enumerate(result.get('results', [])[:2], 1):
                print(f"\n  {j}. {doc.get('title', 'No title')}")
                print(f"     Score: {doc.get('score', 0):.3f}")
                print(f"     Section: {doc.get('section', 'N/A')}")
                
                # Show highlights
                highlights = doc.get('highlights', [])
                if highlights:
                    print(f"     Highlights: {highlights[0][:100]}...")
            
            time.sleep(1)  # Brief pause between queries
    
    def run_ask_demo(self) -> None:
        """Run ask demo"""
        print("\n" + "="*60)
        print("💬 ASK DEMO")
        print("="*60)
        
        for i, question in enumerate(ASK_QUERIES[:2], 1):  # Show first 2 questions
            print(f"\n{i}. Question: {question}")
            print("-" * 50)
            
            start_time = time.time()
            result = self.ask(question)
            ask_time = time.time() - start_time
            
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                continue
            
            print(f"⏱️  Response time: {ask_time:.2f}s")
            
            if result.get('abstained'):
                print(f"🚫 Abstained: {result.get('reason', 'Unknown reason')}")
            else:
                print(f"✅ Answer: {result.get('answer', 'No answer')[:200]}...")
                print(f"📚 Citations: {len(result.get('citations', []))}")
                print(f"📊 Coverage: {result.get('evidence_coverage', 0)*100:.1f}%")
            
            time.sleep(2)  # Longer pause for ask queries
    
    def run_feedback_demo(self) -> None:
        """Run feedback demo"""
        print("\n" + "="*60)
        print("👍 FEEDBACK DEMO")
        print("="*60)
        
        # Get a search result to provide feedback on
        result = self.search("machine learning", top_k=1)
        
        if "error" not in result and result.get('results'):
            doc = result['results'][0]
            print(f"Providing feedback on: {doc.get('title', 'No title')}")
            
            # Submit positive feedback
            feedback_result = self.submit_feedback(
                query="machine learning",
                doc_id=doc.get('doc_id', ''),
                chunk_id=doc.get('chunk_id', ''),
                label="thumbs_up"
            )
            
            if "error" not in feedback_result:
                print(f"✅ Feedback submitted: {feedback_result.get('message', 'Success')}")
            else:
                print(f"❌ Feedback error: {feedback_result['error']}")
    
    def run_performance_test(self) -> None:
        """Run performance test"""
        print("\n" + "="*60)
        print("⚡ PERFORMANCE TEST")
        print("="*60)
        
        search_times = []
        ask_times = []
        
        # Test search performance
        print("Testing search performance...")
        for query in SEARCH_QUERIES[:5]:
            start_time = time.time()
            result = self.search(query, top_k=5)
            search_time = time.time() - start_time
            
            if "error" not in result:
                search_times.append(search_time)
                print(f"  {query[:30]}...: {search_time:.2f}s")
        
        # Test ask performance
        print("\nTesting ask performance...")
        for question in ASK_QUERIES[:3]:
            start_time = time.time()
            result = self.ask(question)
            ask_time = time.time() - start_time
            
            if "error" not in result:
                ask_times.append(ask_time)
                print(f"  {question[:30]}...: {ask_time:.2f}s")
        
        # Summary
        if search_times:
            avg_search_time = sum(search_times) / len(search_times)
            print(f"\n📊 Average search time: {avg_search_time:.2f}s")
        
        if ask_times:
            avg_ask_time = sum(ask_times) / len(ask_times)
            print(f"📊 Average ask time: {avg_ask_time:.2f}s")
    
    def run_full_demo(self) -> None:
        """Run the complete demo"""
        print("🚀 SearchIt Demo Starting...")
        print(f"Gateway URL: {self.gateway_url}")
        
        # Check health
        if not self.check_health():
            print("❌ Gateway is not healthy. Please check if services are running.")
            print("Run: make dev-up")
            return
        
        print("✅ Gateway is healthy")
        
        # Run demos
        self.run_search_demo()
        self.run_ask_demo()
        self.run_feedback_demo()
        self.run_performance_test()
        
        print("\n" + "="*60)
        print("🎉 Demo completed successfully!")
        print("="*60)
        print("\nNext steps:")
        print("1. Open http://localhost:3000 for the web UI")
        print("2. Check http://localhost:8000/docs for API documentation")
        print("3. View metrics at http://localhost:9090 (Prometheus)")
        print("4. View dashboards at http://localhost:3001 (Grafana)")
        print("\n📊 Live metrics available at:")
        print("   - Gateway: http://localhost:8000/metrics")
        print("   - Grafana: http://localhost:3001 (admin/admin)")
        print("   - Prometheus: http://localhost:9090")

def main():
    """Main entry point"""
    demo = SearchItDemo()
    demo.run_full_demo()

if __name__ == "__main__":
    main()
