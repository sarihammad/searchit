.PHONY: setup install dev-up dev-down seed index-toy eval smoke demo fmt lint test clean

# Default target
help:
	@echo "SearchIt - Neural Search Engine with RAG"
	@echo ""
	@echo "Available targets:"
	@echo "  setup       - Install dependencies and setup environment"
	@echo "  install     - Install Python and Node dependencies"
	@echo "  dev-up      - Start all services with Docker Compose"
	@echo "  dev-down    - Stop all services"
	@echo "  seed        - Seed database with initial data"
	@echo "  index-toy   - Index toy corpus through full pipeline"
	@echo "  eval        - Run evaluation harness"
	@echo "  smoke       - Run smoke tests"
	@echo "  demo        - Run demo script with sample queries"
	@echo "  fmt         - Format code with black/prettier"
	@echo "  lint        - Lint code with ruff/eslint"
	@echo "  test        - Run all tests"
	@echo "  clean       - Clean up temporary files"

setup: install
	@echo "Setting up SearchIt..."
	@cp env.example .env
	@echo "✅ Setup complete! Edit .env for configuration."

install:
	@echo "Installing dependencies..."
	@cd services/gateway && pip install -r requirements.txt
	@cd services/indexer && pip install -r requirements.txt
	@cd web && npm install
	@echo "✅ Dependencies installed!"

dev-up:
	@echo "Starting SearchIt services..."
	@docker-compose -f deploy/compose/docker-compose.yml up -d
	@echo "✅ Services started! Waiting for health checks..."
	@sleep 10
	@make smoke

dev-down:
	@echo "Stopping SearchIt services..."
	@docker-compose -f deploy/compose/docker-compose.yml down
	@echo "✅ Services stopped!"

seed:
	@echo "Seeding database..."
	@python services/indexer/pipelines/seed_data.py
	@echo "✅ Database seeded!"

index-toy:
	@echo "Indexing toy corpus..."
	@python services/indexer/pipelines/run_pipeline.py --source eval/datasets/toy_corpus.jsonl
	@echo "✅ Toy corpus indexed!"

eval:
	@echo "Running evaluation harness..."
	@python eval/scripts/run_eval.py --config eval/configs/eval.yaml
	@echo "✅ Evaluation complete!"

eval-report:
	@echo "Generating evaluation report..."
	@python eval/scripts/export_report.py --results eval_results/evaluation_results.json
	@echo "✅ Report generated!"

build-qrels:
	@echo "Building relevance judgments..."
	@python eval/scripts/build_qrels.py --corpus eval/datasets/toy_corpus.jsonl --queries eval/datasets/toy_queries.tsv --output eval/datasets/toy_qrels.tsv --validate
	@echo "✅ Qrels built!"

smoke:
	@echo "Running smoke tests..."
	@curl -s 'http://localhost:8000/health' | grep ok || (echo "❌ Gateway health check failed" && exit 1)
	@curl -s 'http://localhost:8000/search?q=embedding' | grep results || (echo "❌ Search endpoint failed" && exit 1)
	@echo "✅ Smoke tests passed!"

demo: dev-up
	@echo "Running SearchIt demo..."
	@python scripts/demo.py
	@echo "✅ Demo complete! Check output above for URLs and results."

fmt:
	@echo "Formatting code..."
	@cd services/gateway && black . && ruff check --fix .
	@cd services/indexer && black . && ruff check --fix .
	@cd web && npm run format
	@echo "✅ Code formatted!"

lint:
	@echo "Linting code..."
	@cd services/gateway && ruff check . && mypy .
	@cd services/indexer && ruff check . && mypy .
	@cd web && npm run lint
	@echo "✅ Linting complete!"

test:
	@echo "Running tests..."
	@cd services/gateway && pytest tests/ -v
	@cd services/indexer && pytest tests/ -v
	@cd web && npm test
	@echo "✅ Tests passed!"

clean:
	@echo "Cleaning up..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@cd web && rm -rf .next/ out/ build/
	@echo "✅ Cleanup complete!"
