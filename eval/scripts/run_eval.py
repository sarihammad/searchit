#!/usr/bin/env python3
"""
SearchIt Evaluation Script
Runs comprehensive evaluation across different retrieval configurations
"""

import argparse
import json
import logging
import time
from typing import Dict, Any, List, Tuple
import requests
import pandas as pd
import numpy as np
from pathlib import Path
import yaml

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SearchItEvaluator:
    """Evaluator for SearchIt system"""
    
    def __init__(self, gateway_url: str = "http://localhost:8000"):
        self.gateway_url = gateway_url
        self.session = requests.Session()
        self.results = {}
    
    def load_qrels(self, qrels_path: str) -> Dict[str, List[Tuple[str, int]]]:
        """Load relevance judgments from TSV file"""
        qrels = {}
        
        with open(qrels_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('query_id'):
                    parts = line.strip().split('\t')
                    if len(parts) >= 3:
                        query_id = parts[0]
                        doc_id = parts[1]
                        relevance = int(parts[2])
                        
                        if query_id not in qrels:
                            qrels[query_id] = []
                        qrels[query_id].append((doc_id, relevance))
        
        logger.info(f"Loaded {len(qrels)} queries with relevance judgments")
        return qrels
    
    def load_queries(self, queries_path: str) -> Dict[str, str]:
        """Load queries from TSV file"""
        queries = {}
        
        with open(queries_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('query_id'):
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        query_id = parts[0]
                        query_text = parts[1]
                        queries[query_id] = query_text
        
        logger.info(f"Loaded {len(queries)} queries")
        return queries
    
    def search(self, query: str, top_k: int = 100) -> List[Dict[str, Any]]:
        """Perform search and return results"""
        try:
            params = {
                "q": query,
                "top_k": top_k,
                "with_highlights": False
            }
            
            response = self.session.get(f"{self.gateway_url}/search", params=params)
            response.raise_for_status()
            result = response.json()
            
            return result.get('results', [])
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []
    
    def ask(self, question: str, top_k: int = 8) -> Dict[str, Any]:
        """Ask question and return answer"""
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
            logger.error(f"Ask failed for question '{question}': {e}")
            return {"abstained": True, "reason": "error"}
    
    def compute_recall_at_k(self, results: List[Dict[str, Any]], qrels: List[Tuple[str, int]], k: int) -> float:
        """Compute Recall@K"""
        if not qrels:
            return 0.0
        
        # Get top-k doc_ids from results
        retrieved_docs = [r['doc_id'] for r in results[:k]]
        
        # Count relevant documents in top-k
        relevant_in_top_k = sum(1 for doc_id, rel in qrels if doc_id in retrieved_docs and rel > 0)
        
        # Total relevant documents
        total_relevant = sum(1 for _, rel in qrels if rel > 0)
        
        if total_relevant == 0:
            return 0.0
        
        return relevant_in_top_k / total_relevant
    
    def compute_mrr(self, results: List[Dict[str, Any]], qrels: List[Tuple[str, int]]) -> float:
        """Compute Mean Reciprocal Rank"""
        if not qrels:
            return 0.0
        
        # Create relevance map
        relevance_map = {doc_id: rel for doc_id, rel in qrels}
        
        # Find rank of first relevant document
        for i, result in enumerate(results):
            doc_id = result['doc_id']
            if doc_id in relevance_map and relevance_map[doc_id] > 0:
                return 1.0 / (i + 1)
        
        return 0.0
    
    def compute_ndcg_at_k(self, results: List[Dict[str, Any]], qrels: List[Tuple[str, int]], k: int) -> float:
        """Compute NDCG@K"""
        if not qrels:
            return 0.0
        
        # Get relevance scores
        relevance_map = {doc_id: rel for doc_id, rel in qrels}
        
        # DCG@K
        dcg = 0.0
        for i, result in enumerate(results[:k]):
            doc_id = result['doc_id']
            rel = relevance_map.get(doc_id, 0)
            if rel > 0:
                dcg += rel / np.log2(i + 2)  # i+2 because log2(1) = 0
        
        # IDCG@K (ideal DCG)
        ideal_relevances = sorted([rel for _, rel in qrels if rel > 0], reverse=True)
        idcg = 0.0
        for i, rel in enumerate(ideal_relevances[:k]):
            idcg += rel / np.log2(i + 2)
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    def evaluate_search_config(self, config_name: str, queries: Dict[str, str], qrels: Dict[str, List[Tuple[str, int]]]) -> Dict[str, Any]:
        """Evaluate a search configuration"""
        logger.info(f"Evaluating configuration: {config_name}")
        
        metrics = {
            "recall_at_5": [],
            "recall_at_10": [],
            "recall_at_20": [],
            "mrr": [],
            "ndcg_at_10": []
        }
        
        total_queries = 0
        
        for query_id, query_text in queries.items():
            if query_id not in qrels:
                continue
            
            # Perform search
            results = self.search(query_text, top_k=100)
            if not results:
                continue
            
            # Compute metrics
            recall_5 = self.compute_recall_at_k(results, qrels[query_id], 5)
            recall_10 = self.compute_recall_at_k(results, qrels[query_id], 10)
            recall_20 = self.compute_recall_at_k(results, qrels[query_id], 20)
            mrr = self.compute_mrr(results, qrels[query_id])
            ndcg_10 = self.compute_ndcg_at_k(results, qrels[query_id], 10)
            
            metrics["recall_at_5"].append(recall_5)
            metrics["recall_at_10"].append(recall_10)
            metrics["recall_at_20"].append(recall_20)
            metrics["mrr"].append(mrr)
            metrics["ndcg_at_10"].append(ndcg_10)
            
            total_queries += 1
        
        # Compute averages
        avg_metrics = {}
        for metric_name, values in metrics.items():
            avg_metrics[f"avg_{metric_name}"] = np.mean(values) if values else 0.0
            avg_metrics[f"std_{metric_name}"] = np.std(values) if values else 0.0
        
        avg_metrics["total_queries"] = total_queries
        
        logger.info(f"Configuration {config_name}: {total_queries} queries evaluated")
        logger.info(f"  Recall@10: {avg_metrics['avg_recall_at_10']:.3f}")
        logger.info(f"  MRR: {avg_metrics['avg_mrr']:.3f}")
        logger.info(f"  NDCG@10: {avg_metrics['avg_ndcg_at_10']:.3f}")
        
        return avg_metrics
    
    def evaluate_ask_config(self, config_name: str, queries: Dict[str, str]) -> Dict[str, Any]:
        """Evaluate ask configuration"""
        logger.info(f"Evaluating ask configuration: {config_name}")
        
        metrics = {
            "abstain_rate": [],
            "coverage_scores": [],
            "response_times": []
        }
        
        total_queries = 0
        
        for query_id, question in queries.items():
            start_time = time.time()
            result = self.ask(question)
            response_time = time.time() - start_time
            
            metrics["abstain_rate"].append(1 if result.get("abstained", False) else 0)
            metrics["coverage_scores"].append(result.get("evidence_coverage", 0.0))
            metrics["response_times"].append(response_time)
            
            total_queries += 1
        
        # Compute averages
        avg_metrics = {}
        for metric_name, values in metrics.items():
            avg_metrics[f"avg_{metric_name}"] = np.mean(values) if values else 0.0
            avg_metrics[f"std_{metric_name}"] = np.std(values) if values else 0.0
        
        avg_metrics["total_queries"] = total_queries
        
        logger.info(f"Ask configuration {config_name}: {total_queries} queries evaluated")
        logger.info(f"  Abstain rate: {avg_metrics['avg_abstain_rate']:.3f}")
        logger.info(f"  Avg coverage: {avg_metrics['avg_coverage_scores']:.3f}")
        logger.info(f"  Avg response time: {avg_metrics['avg_response_times']:.2f}s")
        
        return avg_metrics
    
    def run_evaluation(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run complete evaluation"""
        logger.info("Starting evaluation...")
        
        # Load data
        queries = self.load_queries(config["queries_path"])
        qrels = self.load_qrels(config["qrels_path"])
        
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "config": config,
            "search_results": {},
            "ask_results": {}
        }
        
        # Evaluate search configurations
        search_configs = config.get("search_configs", [])
        for search_config in search_configs:
            config_name = search_config["name"]
            results["search_results"][config_name] = self.evaluate_search_config(
                config_name, queries, qrels
            )
        
        # Evaluate ask configurations
        ask_configs = config.get("ask_configs", [])
        for ask_config in ask_configs:
            config_name = ask_config["name"]
            results["ask_results"][config_name] = self.evaluate_ask_config(
                config_name, queries
            )
        
        return results
    
    def save_results(self, results: Dict[str, Any], output_path: str):
        """Save evaluation results"""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_path}")
    
    def generate_report(self, results: Dict[str, Any], output_path: str):
        """Generate evaluation report"""
        report_lines = []
        
        report_lines.append("# SearchIt Evaluation Report")
        report_lines.append(f"Generated: {results['timestamp']}")
        report_lines.append("")
        
        # Search results
        report_lines.append("## Search Results")
        report_lines.append("")
        
        search_results = results.get("search_results", {})
        if search_results:
            # Create summary table
            report_lines.append("| Configuration | Recall@10 | MRR | NDCG@10 | Queries |")
            report_lines.append("|---------------|-----------|-----|---------|---------|")
            
            for config_name, metrics in search_results.items():
                recall_10 = metrics.get("avg_recall_at_10", 0.0)
                mrr = metrics.get("avg_mrr", 0.0)
                ndcg_10 = metrics.get("avg_ndcg_at_10", 0.0)
                queries = metrics.get("total_queries", 0)
                
                report_lines.append(f"| {config_name} | {recall_10:.3f} | {mrr:.3f} | {ndcg_10:.3f} | {queries} |")
        
        report_lines.append("")
        
        # Ask results
        report_lines.append("## Ask Results")
        report_lines.append("")
        
        ask_results = results.get("ask_results", {})
        if ask_results:
            # Create summary table
            report_lines.append("| Configuration | Abstain Rate | Avg Coverage | Avg Time (s) | Queries |")
            report_lines.append("|---------------|--------------|--------------|--------------|---------|")
            
            for config_name, metrics in ask_results.items():
                abstain_rate = metrics.get("avg_abstain_rate", 0.0)
                coverage = metrics.get("avg_coverage_scores", 0.0)
                response_time = metrics.get("avg_response_times", 0.0)
                queries = metrics.get("total_queries", 0)
                
                report_lines.append(f"| {config_name} | {abstain_rate:.3f} | {coverage:.3f} | {response_time:.2f} | {queries} |")
        
        report_lines.append("")
        
        # Detailed results
        report_lines.append("## Detailed Results")
        report_lines.append("")
        
        for config_name, metrics in search_results.items():
            report_lines.append(f"### {config_name}")
            report_lines.append("")
            
            for metric_name, value in metrics.items():
                if metric_name.startswith("avg_"):
                    report_lines.append(f"- **{metric_name}**: {value:.4f}")
            
            report_lines.append("")
        
        # Save report
        with open(output_path, 'w') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"Report saved to {output_path}")
    
    def check_regression(self, results: Dict[str, Any], baseline_path: str, epsilon: float = 0.01) -> bool:
        """Check for regressions against baseline metrics"""
        try:
            with open(baseline_path, 'r') as f:
                baseline = json.load(f)
            
            regression_detected = False
            
            # Check search results
            baseline_search = baseline.get("search_results", {})
            current_search = results.get("search_results", {})
            
            for config_name in baseline_search:
                if config_name in current_search:
                    baseline_metrics = baseline_search[config_name]
                    current_metrics = current_search[config_name]
                    
                    # Check key metrics for regression
                    key_metrics = ["avg_recall_at_10", "avg_mrr", "avg_ndcg_at_10"]
                    
                    for metric in key_metrics:
                        baseline_val = baseline_metrics.get(metric, 0.0)
                        current_val = current_metrics.get(metric, 0.0)
                        
                        if current_val < baseline_val - epsilon:
                            logger.warning(f"Regression in {config_name}.{metric}: {current_val:.3f} < {baseline_val:.3f} (threshold: {baseline_val - epsilon:.3f})")
                            regression_detected = True
            
            # Check ask results
            baseline_ask = baseline.get("ask_results", {})
            current_ask = results.get("ask_results", {})
            
            for config_name in baseline_ask:
                if config_name in current_ask:
                    baseline_metrics = baseline_ask[config_name]
                    current_metrics = current_ask[config_name]
                    
                    # Check abstain rate (should not increase significantly)
                    baseline_abstain = baseline_metrics.get("avg_abstain_rate", 0.0)
                    current_abstain = current_metrics.get("avg_abstain_rate", 0.0)
                    
                    if current_abstain > baseline_abstain + epsilon:
                        logger.warning(f"Regression in {config_name}.avg_abstain_rate: {current_abstain:.3f} > {baseline_abstain:.3f} (threshold: {baseline_abstain + epsilon:.3f})")
                        regression_detected = True
            
            return regression_detected
            
        except Exception as e:
            logger.error(f"Failed to check regression: {e}")
            return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run SearchIt evaluation")
    parser.add_argument("--config", required=True, help="Configuration file path")
    parser.add_argument("--output", help="Output directory for results")
    parser.add_argument("--gateway", default="http://localhost:8000", help="Gateway URL")
    
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Set output directory
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = Path("eval_results")
        output_dir.mkdir(exist_ok=True)
    
    # Run evaluation
    evaluator = SearchItEvaluator(args.gateway)
    results = evaluator.run_evaluation(config)
    
    # Save results
    results_path = output_dir / "evaluation_results.json"
    evaluator.save_results(results, str(results_path))
    
    # Also save as latest.json for CI comparison
    latest_path = Path("eval/runs/latest.json")
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    evaluator.save_results(results, str(latest_path))
    
    # Generate report
    report_path = output_dir / "evaluation_report.md"
    evaluator.generate_report(results, str(report_path))
    
    # Check for regressions against baseline
    baseline_path = Path("eval/baselines/baseline_metrics.json")
    if baseline_path.exists():
        regression_detected = evaluator.check_regression(results, str(baseline_path))
        if regression_detected:
            logger.error("REGRESSION DETECTED: Performance below baseline thresholds")
            exit(1)
        else:
            logger.info("No regressions detected - performance within acceptable thresholds")
    
    logger.info("Evaluation completed!")

if __name__ == "__main__":
    main()
