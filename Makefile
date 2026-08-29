.PHONY: setup pipeline dashboard

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
