doc: dad dad/* Makefile
	@mkdir -p doc
	epydoc -o doc/html dad

_trial_temp/coverage: dad/*.py dad/*/*.py
	trial --coverage dad.test

coverage: _trial_temp/coverage
	python misc/show-coverage.py `ls _trial_temp/coverage/dad* | grep -v dad.extern | grep -v dad.test`

