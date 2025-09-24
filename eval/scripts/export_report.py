#!/usr/bin/env python3
"""
Export evaluation report with visualizations
"""

import argparse
import json
import logging
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ReportExporter:
    """Export evaluation reports with visualizations"""
    
    def __init__(self, results_path: str):
        with open(results_path, 'r') as f:
            self.results = json.load(f)
        
        # Set plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    def create_search_metrics_plot(self, output_path: str):
        """Create plot for search metrics"""
        search_results = self.results.get("search_results", {})
        if not search_results:
            logger.warning("No search results to plot")
            return
        
        # Prepare data
        configs = []
        recall_10 = []
        mrr = []
        ndcg_10 = []
        
        for config_name, metrics in search_results.items():
            configs.append(config_name)
            recall_10.append(metrics.get("avg_recall_at_10", 0.0))
            mrr.append(metrics.get("avg_mrr", 0.0))
            ndcg_10.append(metrics.get("avg_ndcg_at_10", 0.0))
        
        # Create subplots
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        # Recall@10
        axes[0].bar(configs, recall_10, color='skyblue', alpha=0.7)
        axes[0].set_title('Recall@10')
        axes[0].set_ylabel('Score')
        axes[0].tick_params(axis='x', rotation=45)
        
        # MRR
        axes[1].bar(configs, mrr, color='lightgreen', alpha=0.7)
        axes[1].set_title('Mean Reciprocal Rank')
        axes[1].set_ylabel('Score')
        axes[1].tick_params(axis='x', rotation=45)
        
        # NDCG@10
        axes[2].bar(configs, ndcg_10, color='lightcoral', alpha=0.7)
        axes[2].set_title('NDCG@10')
        axes[2].set_ylabel('Score')
        axes[2].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Search metrics plot saved to {output_path}")
    
    def create_ask_metrics_plot(self, output_path: str):
        """Create plot for ask metrics"""
        ask_results = self.results.get("ask_results", {})
        if not ask_results:
            logger.warning("No ask results to plot")
            return
        
        # Prepare data
        configs = []
        abstain_rate = []
        coverage = []
        response_time = []
        
        for config_name, metrics in ask_results.items():
            configs.append(config_name)
            abstain_rate.append(metrics.get("avg_abstain_rate", 0.0))
            coverage.append(metrics.get("avg_coverage_scores", 0.0))
            response_time.append(metrics.get("avg_response_times", 0.0))
        
        # Create subplots
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        # Abstain Rate
        axes[0].bar(configs, abstain_rate, color='orange', alpha=0.7)
        axes[0].set_title('Abstain Rate')
        axes[0].set_ylabel('Rate')
        axes[0].tick_params(axis='x', rotation=45)
        
        # Coverage
        axes[1].bar(configs, coverage, color='purple', alpha=0.7)
        axes[1].set_title('Evidence Coverage')
        axes[1].set_ylabel('Score')
        axes[1].tick_params(axis='x', rotation=45)
        
        # Response Time
        axes[2].bar(configs, response_time, color='brown', alpha=0.7)
        axes[2].set_title('Response Time')
        axes[2].set_ylabel('Seconds')
        axes[2].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Ask metrics plot saved to {output_path}")
    
    def create_comparison_plot(self, output_path: str):
        """Create comparison plot for all metrics"""
        search_results = self.results.get("search_results", {})
        ask_results = self.results.get("ask_results", {})
        
        if not search_results and not ask_results:
            logger.warning("No results to plot")
            return
        
        # Prepare data
        data = []
        
        # Search metrics
        for config_name, metrics in search_results.items():
            data.append({
                'Configuration': config_name,
                'Metric': 'Recall@10',
                'Score': metrics.get("avg_recall_at_10", 0.0)
            })
            data.append({
                'Configuration': config_name,
                'Metric': 'MRR',
                'Score': metrics.get("avg_mrr", 0.0)
            })
            data.append({
                'Configuration': config_name,
                'Metric': 'NDCG@10',
                'Score': metrics.get("avg_ndcg_at_10", 0.0)
            })
        
        # Ask metrics (normalized)
        for config_name, metrics in ask_results.items():
            data.append({
                'Configuration': config_name,
                'Metric': 'Coverage',
                'Score': metrics.get("avg_coverage_scores", 0.0)
            })
            data.append({
                'Configuration': config_name,
                'Metric': '1-Abstain Rate',
                'Score': 1.0 - metrics.get("avg_abstain_rate", 0.0)
            })
        
        if not data:
            logger.warning("No data to plot")
            return
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Create plot
        plt.figure(figsize=(12, 8))
        sns.barplot(data=df, x='Configuration', y='Score', hue='Metric')
        plt.title('SearchIt Evaluation Results Comparison')
        plt.ylabel('Score')
        plt.xticks(rotation=45)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Comparison plot saved to {output_path}")
    
    def export_to_html(self, output_path: str):
        """Export results to HTML report"""
        html_content = []
        
        html_content.append("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SearchIt Evaluation Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .metric-good { color: green; font-weight: bold; }
                .metric-bad { color: red; font-weight: bold; }
                .metric-neutral { color: black; }
            </style>
        </head>
        <body>
        """)
        
        html_content.append(f"<h1>SearchIt Evaluation Report</h1>")
        html_content.append(f"<p><strong>Generated:</strong> {self.results.get('timestamp', 'Unknown')}</p>")
        
        # Search results
        search_results = self.results.get("search_results", {})
        if search_results:
            html_content.append("<h2>Search Results</h2>")
            html_content.append("<table>")
            html_content.append("<tr><th>Configuration</th><th>Recall@10</th><th>MRR</th><th>NDCG@10</th><th>Queries</th></tr>")
            
            for config_name, metrics in search_results.items():
                recall_10 = metrics.get("avg_recall_at_10", 0.0)
                mrr = metrics.get("avg_mrr", 0.0)
                ndcg_10 = metrics.get("avg_ndcg_at_10", 0.0)
                queries = metrics.get("total_queries", 0)
                
                html_content.append(f"<tr>")
                html_content.append(f"<td>{config_name}</td>")
                html_content.append(f"<td>{recall_10:.3f}</td>")
                html_content.append(f"<td>{mrr:.3f}</td>")
                html_content.append(f"<td>{ndcg_10:.3f}</td>")
                html_content.append(f"<td>{queries}</td>")
                html_content.append(f"</tr>")
            
            html_content.append("</table>")
        
        # Ask results
        ask_results = self.results.get("ask_results", {})
        if ask_results:
            html_content.append("<h2>Ask Results</h2>")
            html_content.append("<table>")
            html_content.append("<tr><th>Configuration</th><th>Abstain Rate</th><th>Coverage</th><th>Response Time (s)</th><th>Queries</th></tr>")
            
            for config_name, metrics in ask_results.items():
                abstain_rate = metrics.get("avg_abstain_rate", 0.0)
                coverage = metrics.get("avg_coverage_scores", 0.0)
                response_time = metrics.get("avg_response_times", 0.0)
                queries = metrics.get("total_queries", 0)
                
                html_content.append(f"<tr>")
                html_content.append(f"<td>{config_name}</td>")
                html_content.append(f"<td>{abstain_rate:.3f}</td>")
                html_content.append(f"<td>{coverage:.3f}</td>")
                html_content.append(f"<td>{response_time:.2f}</td>")
                html_content.append(f"<td>{queries}</td>")
                html_content.append(f"</tr>")
            
            html_content.append("</table>")
        
        html_content.append("</body></html>")
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(html_content))
        
        logger.info(f"HTML report saved to {output_path}")
    
    def export_to_csv(self, output_path: str):
        """Export results to CSV"""
        search_results = self.results.get("search_results", {})
        ask_results = self.results.get("ask_results", {})
        
        # Prepare data
        rows = []
        
        # Search results
        for config_name, metrics in search_results.items():
            row = {
                'Type': 'Search',
                'Configuration': config_name,
                'Recall@10': metrics.get("avg_recall_at_10", 0.0),
                'MRR': metrics.get("avg_mrr", 0.0),
                'NDCG@10': metrics.get("avg_ndcg_at_10", 0.0),
                'Total_Queries': metrics.get("total_queries", 0)
            }
            rows.append(row)
        
        # Ask results
        for config_name, metrics in ask_results.items():
            row = {
                'Type': 'Ask',
                'Configuration': config_name,
                'Abstain_Rate': metrics.get("avg_abstain_rate", 0.0),
                'Coverage': metrics.get("avg_coverage_scores", 0.0),
                'Response_Time': metrics.get("avg_response_times", 0.0),
                'Total_Queries': metrics.get("total_queries", 0)
            }
            rows.append(row)
        
        if rows:
            df = pd.DataFrame(rows)
            df.to_csv(output_path, index=False)
            logger.info(f"CSV report saved to {output_path}")
        else:
            logger.warning("No data to export to CSV")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Export evaluation report")
    parser.add_argument("--results", required=True, help="Results JSON file path")
    parser.add_argument("--output", help="Output directory")
    
    args = parser.parse_args()
    
    # Set output directory
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = Path("eval_results")
        output_dir.mkdir(exist_ok=True)
    
    # Create exporter
    exporter = ReportExporter(args.results)
    
    # Generate visualizations
    exporter.create_search_metrics_plot(str(output_dir / "search_metrics.png"))
    exporter.create_ask_metrics_plot(str(output_dir / "ask_metrics.png"))
    exporter.create_comparison_plot(str(output_dir / "comparison.png"))
    
    # Export reports
    exporter.export_to_html(str(output_dir / "report.html"))
    exporter.export_to_csv(str(output_dir / "results.csv"))
    
    logger.info("Report export completed!")

if __name__ == "__main__":
    main()
