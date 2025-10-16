# TERVYX Protocol Makefile
# Provides convenient targets for common development tasks aligned with the TEL-5 pipeline

.PHONY: init install new build validate test clean lint format help status

# Default target
help:
	@echo "TERVYX Protocol - Available Commands:"
	@echo "=================================="
	@echo "  init        Initialize development environment"
	@echo "  install     Install Python dependencies"
	@echo "  new         Create sample entry"
	@echo "  build       Build sample entry"  
	@echo "  validate    Validate sample entry artifacts"
	@echo "  test        Run all tests and validations"
	@echo "  lint        Run code linting"
	@echo "  format      Format code with black (if available)"
	@echo "  status      Show system status"
	@echo "  clean       Clean generated files"
	@echo "  help        Show this help message"

# Initialize development environment
init: install
	@echo "🚀 TERVYX Protocol initialized successfully"
	@python scripts/tervyx.py fingerprint

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	python -m pip install --upgrade pip
	pip install -r requirements.txt

# Create sample entry
new:
	@echo "📝 Creating sample entry..."
	python scripts/tervyx.py new nutrient magnesium-glycinate sleep

# Build sample entry  
build:
	@echo "🔨 Building sample entry..."
	python scripts/tervyx.py build entries/nutrient/magnesium-glycinate/sleep/v1 --category sleep

# Validate sample entry
validate:
	@echo "✅ Validating sample entry..."
	python scripts/tervyx.py validate entries/nutrient/magnesium-glycinate/sleep/v1
	python engine/schema_validate.py entries/nutrient/magnesium-glycinate/sleep/v1

# Run comprehensive tests
test: validate
	@echo "🧪 Running comprehensive tests..."
	@echo "Policy fingerprint:"
	@python scripts/tervyx.py fingerprint
	@echo ""
	@echo "System status:"
	@python scripts/tervyx.py status
	@echo ""
	@echo "Checking reproducibility..."
	@python scripts/tervyx.py build entries/nutrient/magnesium-glycinate/sleep/v1 --category sleep
	@python scripts/tervyx.py validate entries/nutrient/magnesium-glycinate/sleep/v1
	@echo "✅ All tests passed"

# Lint code
lint:
	@echo "🔍 Linting code..."
	@command -v flake8 >/dev/null 2>&1 || { echo "Installing flake8..."; pip install flake8; }
	flake8 engine scripts --max-line-length=127 --extend-ignore=E203,W503

# Format code (optional)
format:
	@echo "🎨 Formatting code..."
	@command -v black >/dev/null 2>&1 || { echo "Installing black..."; pip install black; }
	black engine scripts --line-length=127

# Show system status
status:
	@python scripts/tervyx.py status

# Clean generated files
clean:
	@echo "🧹 Cleaning generated files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -f AUDIT_LOG.jsonl
	rm -rf entries/nutrient/magnesium-glycinate/sleep/v1/simulation.json
	rm -rf entries/nutrient/magnesium-glycinate/sleep/v1/entry.jsonld
	@echo "✅ Cleanup complete"

# Development workflow
dev: init new build validate
	@echo "🎉 Development setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  - Edit entries/nutrient/magnesium-glycinate/sleep/v1/evidence.csv"
	@echo "  - Run 'make build' to rebuild"
	@echo "  - Run 'make test' to validate everything"

# CI simulation (run all CI checks locally)
ci: lint test
	@echo "🚀 CI simulation complete - ready for push!"