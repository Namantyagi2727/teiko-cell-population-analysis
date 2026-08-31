.PHONY: setup pipeline dashboard test clean

setup:
	python3 -m pip install --upgrade pip
	python3 -m pip install -r requirements.txt

pipeline:
	python3 load_data.py
	python3 analysis/part2_frequencies.py
	python3 analysis/part3_stats.py
	python3 analysis/part4_subset.py

dashboard:
	streamlit run dashboard/app.py

# Extra targets, not required by the assignment spec (only setup/pipeline/
# dashboard are), kept here for convenience during development and CI.
test:
	python3 -m pytest tests/ -v

clean:
	rm -f cell_counts.db
	rm -rf output
	rm -rf .pytest_cache
	find . -name "__pycache__" -type d -exec rm -rf {} +
