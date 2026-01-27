CHAPTER ?=

.check_chapter:
	@if [ -z "$(CHAPTER)" ]; then \
		echo "Error: CHAPTER parameter is required"; \
		echo "Usage: make test CHAPTER=3"; \
		exit 1; \
	fi

test: .check_chapter
	@echo "Running test with test_runner.py..."
	python3 test_runner.py $(CHAPTER)

clean:
	@rm -f stdout-ch*
	@rm -rf temp-*
	@echo "Cleanup completed"

help:
	@echo "ustb-os-checker - Usage"
	@echo ""
	@echo "Basic Usage:"
	@echo "  make test CHAPTER=3"
	@echo ""
	@echo "Directory Structure:"
	@echo "  ustb-os-kernel/"
	@echo "  ├── kernel/                   # OS kernel code"
	@echo "  ├── user/                     # User programs"
	@echo "  └── ustb-os-checker/          # This checker"
	@echo ""
	@echo "Other Commands:"
	@echo "  make clean                    # Clean temporary files"
	@echo "  python3 config.py             # Check configuration"

check-config:
	@python3 config.py

.PHONY: test clean help check-config .check_chapter