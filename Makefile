.PHONY: all data refresh serve clean check gzip

PY ?= python3
PORT ?= 8000

all: data

## data: fetch third-party sources and rebuild every derived file in web/data/
data:
	$(PY) scripts/build_all.py

## refresh: re-download sources even if cached, then rebuild
refresh:
	$(PY) scripts/fetch_sources.py --force
	$(PY) scripts/build_all.py

## serve: static server for web/ (the views fetch JSON, so file:// will not work)
## Serves pre-compressed .json.gz when present; run `make gzip` to create them.
serve:
	@echo "http://localhost:$(PORT)/"
	@$(PY) scripts/serve.py $(PORT)

## check: re-run the validators without re-downloading anything
check:
	$(PY) scripts/build_timeline.py

## gzip: pre-compress the generated JSON so `make serve` can send it compressed
gzip:
	$(PY) scripts/gzip_data.py

## clean: remove generated files (keeps data/raw/ so you need not re-download)
clean:
	rm -rf web/data/text web/data/xref web/data/tr web/data/*.json web/data/*.gz
	find web/data -name '*.json.gz' -delete 2>/dev/null || true
