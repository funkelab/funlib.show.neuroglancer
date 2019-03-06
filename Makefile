default:
	pip install -r requirements.txt
	pip install .

install-dev:
	pip install -r requirements.txt
	pip install -e .
