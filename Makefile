version := $(shell python -c 'from mash.version import __VERSION__; print(__VERSION__)')

build: check test
	rm -f dist/*
	# delete version information from setup.py for rpm package
	# we don't want to have this in the egg info because the rpm
	# package should handle package/version requirements
	cat setup.py | sed -e 's@>=[0-9.]*@@g' > setup.build.py
	python setup.build.py sdist
	rm setup.build.py
	cat package/mash-spec-template | sed -e s'@%%VERSION@${version}@' \
		> dist/mash.spec

.PHONY: test
test:
	cd test/unit && \
	py.test --no-cov-on-fail --cov=mash \
		--cov-report=term-missing --cov-fail-under=100 --cov-config .coveragerc

check:
	flake8 --statistics -j auto --count mash
	flake8 --statistics -j auto --count test/unit
