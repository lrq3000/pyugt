# This Makefile runs tests and builds the package to upload to pypi
# To use this Makefile, pip install py3make
# then do: py3make <command>
# or: python.exe -m py3make <command>
# You also need to pip install also other required modules: `pip install flake8 coverage twine pytest pytest-cov validate-pyproject[all] pytest-xdist rstcheck` , or simply `pip install --editable .[test,testmeta]`
#
# IMPORTANT: for compatibility with `python setup.py make [alias]`, ensure:
# 1. Every alias is preceded by @[+]make (eg: @make alias)
# 2. A maximum of one @make alias or command per line
#
# Sample makefile compatible with `python setup.py make`:
#```
#all:
#	@make test
#	@make install
#test:
#	nosetest
#install:
#	python setup.py install
#```

help:
	@+make -p

alltests:
	@+make testcoverage
	@+make testsetup

all:
	@make alltests
	@make build

prebuildclean:
	@+python -c "import shutil; shutil.rmtree('build', True)"
	@+python -c "import shutil; shutil.rmtree('dist', True)"
	@+python -c "import shutil; shutil.rmtree('pyugt.egg-info', True)"  # very important to delete egg-info before any new build or pip install, otherwise may cause an error that multiple egg-info folders are present, or it may build using old definitions

coverclean:
	@+python -c "import os; os.remove('.coverage') if os.path.exists('.coverage') else None"
	@+python -c "import shutil; shutil.rmtree('__pycache__', True)"
	@+python -c "import shutil; shutil.rmtree('tests/__pycache__', True)"

test:
	#tox --skip-missing-interpreters
    pytest

testpyproject:
	validate-pyproject pyproject.toml -v

testsetuppost:
	twine check "dist/*"

testrst:
	rstcheck README.rst

testcoverage:
	@+make coverclean
	coverage run --branch -m pytest -v
	coverage report -m

testmalloc:
	@+python -X dev -X tracemalloc=5 -m pytest

testasv:
	asv run -j 8 HEAD~3..HEAD
	@make viewasv

testasvfull:
	asv run -j 8 v1.0.0..master
	@make testasv

viewasv:
	asv publish
	asv preview

installdev:
	@+make prebuildclean
	@+python -m pip install --upgrade --editable .[test,testmeta] --verbose --use-pep517

install:
	@+make prebuildclean
	@+python -m pip install --upgrade . --verbose --use-pep517

build:
	# requires `pip install build`
	#@+make testrst
	@+make prebuildclean
	@+make testpyproject
	@+python -sBm build  # do NOT use the -w flag, otherwise only the wheel will be built, but we need sdist for source distros such as Debian and Gentoo!
	@+make testsetuppost

buildwheelhouse:
	cibuildwheel --platform auto

upload:
	twine upload dist/*

buildupload:
	#@+make testsetup
	@+make build
	@+make upload
