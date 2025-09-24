# SearchIt Evaluation Guide

## Overview

SearchIt includes a comprehensive evaluation harness to measure and track the performance of different search and RAG configurations. The evaluation system supports both retrieval metrics (Recall@K, MRR, NDCG@K) and generation metrics (abstain rate, coverage, response time).

## Evaluation Metrics

### Search Metrics

- **Recall@K**: Proportion of relevant documents retrieved in top-K results
- **Mean Reciprocal Rank (MRR)**: Average reciprocal rank of first relevant document
- **Normalized Discounted Cumulative Gain (NDCG@K)**: Quality of ranking considering position and relevance

### Ask Metrics

- **Abstain Rate**: Proportion of queries where the system abstains from answering
- **Evidence Coverage**: Average coverage score of retrieved evidence
- **Response Time**: Average time to generate answers

## Quick Start

```bash
# 1. Build relevance judgments (qrels)
make build-qrels

# 2. Run evaluation
make eval

# 3. Generate report with visualizations
make eval-report
```

## Configuration

Evaluation is configured through `eval/configs/eval.yaml`:

```yaml
# Dataset paths
queries_path: "eval/datasets/toy_queries.tsv"
qrels_path: "eval/datasets/toy_qrels.tsv"

# Search configurations to evaluate
search_configs:
  - name: "Hybrid_RRF"
    description: "Hybrid search with RRF fusion"

# Ask configurations to evaluate
ask_configs:
  - name: "Default"
    description: "Default ask configuration"
```

## Dataset Format

### Queries (TSV)

```
query_id	query_text
1	What is machine learning?
2	How do neural networks work?
```

### Relevance Judgments (TSV)

```
query_id	doc_id	relevance
1	doc1	2
1	doc2	1
```

Where relevance scores are:

- `0`: Not relevant
- `1`: Relevant
- `2`: Highly relevant

### Corpus (JSONL)

```json
{"doc_id": "doc1", "title": "Machine Learning", "text": "...", "tags": ["ml"]}
{"doc_id": "doc2", "title": "Neural Networks", "text": "...", "tags": ["ai"]}
```

## Running Evaluation

### Command Line

```bash
# Basic evaluation
python eval/scripts/run_eval.py --config eval/configs/eval.yaml

# With custom output directory
python eval/scripts/run_eval.py --config eval/configs/eval.yaml --output my_results

# With custom gateway URL
python eval/scripts/run_eval.py --config eval/configs/eval.yaml --gateway http://localhost:8000
```

### Programmatic

```python
from eval.scripts.run_eval import SearchItEvaluator

evaluator = SearchItEvaluator("http://localhost:8000")
results = evaluator.run_evaluation(config)
```

## Baseline Comparison

The evaluation system supports baseline comparison to detect regressions:

```yaml
baseline:
  enabled: true
  file: "eval/baselines/baseline_metrics.json"
  thresholds:
    recall_at_10:
      regression_threshold: 0.05 # 5% regression threshold
    mrr:
      regression_threshold: 0.03
```

## Results and Reports

### JSON Results

```json
{
  "timestamp": "2024-01-01 12:00:00",
  "search_results": {
    "Hybrid_RRF": {
      "avg_recall_at_10": 0.75,
      "avg_mrr": 0.62,
      "avg_ndcg_at_10": 0.68
    }
  },
  "ask_results": {
    "Default": {
      "avg_abstain_rate": 0.15,
      "avg_coverage_scores": 0.78
    }
  }
}
```

### Markdown Report

```markdown
# SearchIt Evaluation Report

## Search Results

| Configuration | Recall@10 | MRR   | NDCG@10 |
| ------------- | --------- | ----- | ------- |
| Hybrid_RRF    | 0.750     | 0.620 | 0.680   |
```

### Visualizations

- Bar charts for metric comparisons
- Time series plots for performance trends
- Heatmaps for configuration analysis

## CI Integration

Add to `.github/workflows/ci.yml`:

```yaml
- name: Run Evaluation
  run: |
    make dev-up
    sleep 30
    make index-toy
    make eval

    # Check for regressions
    python scripts/check_regression.py --baseline eval/baselines/baseline_metrics.json --results eval_results/evaluation_results.json
```

## Custom Evaluations

### Adding New Metrics

```python
def compute_custom_metric(self, results, qrels):
    # Implementation
    return metric_value
```

### Custom Configurations

```yaml
search_configs:
  - name: "Custom_Config"
    description: "Custom search configuration"
    parameters:
      rrf_k: 100
      top_k: 50
```

## Troubleshooting

### Common Issues

1. **Gateway not responding**: Ensure services are running with `make dev-up`
2. **No results found**: Check if corpus is indexed with `make index-toy`
3. **Evaluation timeout**: Increase timeout in config or reduce query count

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python eval/scripts/run_eval.py --config eval/configs/eval.yaml
```

## Best Practices

1. **Regular Evaluation**: Run evaluation on every significant change
2. **Baseline Updates**: Update baselines after performance improvements
3. **Statistical Significance**: Use sufficient queries for reliable metrics
4. **Configuration Tracking**: Version control evaluation configurations
5. **Automated Alerts**: Set up alerts for performance regressions

## Advanced Usage

### A/B Testing

```python
# Compare two configurations
config_a = {"rrf_k": 60}
config_b = {"rrf_k": 100}

results_a = evaluator.evaluate_config(config_a)
results_b = evaluator.evaluate_config(config_b)
```

### Statistical Analysis

```python
import scipy.stats

# Perform statistical significance test
statistic, p_value = scipy.stats.ttest_rel(results_a, results_b)
```

### Custom Datasets

```python
# Load custom dataset
custom_queries = load_custom_queries("my_queries.json")
custom_qrels = load_custom_qrels("my_qrels.tsv")
```

## Performance Considerations

- **Parallel Evaluation**: Use multiple workers for faster evaluation
- **Caching**: Cache embeddings and search results
- **Sampling**: Use query sampling for large datasets
- **Incremental**: Support incremental evaluation for updates

## Integration with Monitoring

- **Prometheus Metrics**: Export evaluation metrics to Prometheus
- **Grafana Dashboards**: Visualize evaluation trends
- **Alerting**: Set up alerts for performance regressions
- **Logging**: Structured logging for evaluation runs
