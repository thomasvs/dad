trial:
	trial dadcouch.test

_trial_temp/coverage: python/dadcouch python/dadcouch/*.py python/dadcouch/*/*.py
	trial --coverage dadcouch.test

coverage: _trial_temp/coverage
	find _trial_temp/coverage -name 'dadcouch.*.cover' | grep -v dadcouch.test | grep -v paisley.mapping | xargs scripts/show-coverage.py

clean:
	find python -name '*.pyc' -exec rm {} \;

pep8:
	find python/dadcouch -name '*.py' | grep -v paisley/mapping.py | xargs scripts/pep8.py --repeat

check: trial pep8

doc: python/dadcouch Makefile
	@mkdir -p doc
	PYTHONPATH=$$PYTHONPATH:python/dadcouch/extern epydoc -v -o doc/html --exclude test.test_ misc/epyhelp.py dad dadgst dadcouch dadgtk

DB=dad

push:
	couchapp push --docid _design/dad couchdb http://localhost:5984/$(DB)
