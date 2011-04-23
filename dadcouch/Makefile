trial:
	trial dadcouch.test

coverage: python/dadcouch
	trial --coverage dadcouch.test
	find _trial_temp/coverage -name 'dadcouch.*.cover' | grep -v dadcouch.test | grep -v paisley.mapping | xargs scripts/show-coverage.py

clean:
	find python -name '*.pyc' -exec rm {} \;

pep8:
	find python/dadcouch -name '*.py' | grep -v paisley/mapping.py | xargs scripts/pep8.py --repeat

check: trial pep8
