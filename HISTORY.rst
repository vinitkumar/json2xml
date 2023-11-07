History
=======

4.1.0 / 2023-11-07
==================

 * chore(deps): bump urllib3 from 1.26.13 to 1.26.18 (#192, #195)

4.0.1 / 2023-10-13
==================

  * feat: get local working for 3.12 and fix some code quality issue
  * Fix/make docs better (#186)
  * fix: issue with hardcoded year
  * feat: upgrade sphinx theme
  * fix: issues with ruff linting, use isinstance in place of type
  * fix: make readme better
  * chore(deps): bump tornado from 6.3.2 to 6.3.3 in /docs (#185)
  * chore(deps): bump certifi from 2022.12.7 to 2023.7.22 in /docs (#183)
  * chore(deps): bump pygments from 2.10.0 to 2.15.0 in /docs (#182)

4.0.0 / 2023-07-19
==================

  * Updated to Python 3.12 beta 4
  * Added check for pypy 3.10
  * Dropped support for Python 3.7
  * Updated fixture for attrs with dict and removed comment (#170)

3.21.0 / 2023-01-18
===================

  * Implemented list item with attributes (#169)
  * Added python3.12 alpha4 to the fix (#168)
  * Replaced requests with urllib3 (#167)
  * Added security reporting guidelines
  * Added CodeQL workflow for GitHub code scanning (#160)
  * Set default to False for list_headers (#164)
  * Fixed ci issue due to mypy update on python3.11 (#166)
  * Updated certifi from 2021.10.8 to 2022.12.7 in /docs (#162)
  * Fixed file opening issue
  * Celebrated release of Python 3.11 (#159)

3.20.0 / 2022-10-16
===================

  * Made dependencies more flexible (#158)
  * Used SystemRandom for secure random integer generation (#156)

3.19.5 / 2022-09-18
===================

  * Fixed issues #138 and #151, added 2 new unit tests (#154)
  * Fixed unit tests for #152 (#153)

3.19.4 / 2022-07-24
===================

  * Transitioned from unittest to pytest (#149)
  * Upgraded python test to python311beta (#148)
  * Tested new version of 3.10 and 3.11 (#147)

3.19.3 / 2022-07-01
===================

  * Added UTF-8 encoding type to @readfromjson function in utils.py for Korean language support (#145)

3.19.2 / 2022-06-09
===================

  * Escaped xml char when having attrs (#144)
  * Adjusted pytest config setting for easier logging
  * Bumped python 3.10 and 3.11 version (#142)

3.19.1 / 2022-06-05
===================

  * Bumped version of docs building
  * Updated waitress from 2.1.1 to 2.1.2 in /docs (#141)
  * Updated docs for dicttoxml (#140)

3.19.0 / 2022-05-20
===================

  * Set xsi location (#135)
  * Repeated list headers (#138)
  * Added support for python3.11 (#139)
  * Improved docs for dicttoxml (#134)
  * Fixed types working check for ci mypy (#133)
  * Added mypy support to ci (#132)
  * Generated changelog
  * Removed logging by default (#131)
  * Merged two dev requirements files (#129)
  * Removed old unused config
  * Added types (#125)
  * Fixed issue with twine check
  * Fixed issue with long description
  * Refactored: xmltodict is only test dependency now (#124)
  * Added correct list of contributors
  * Generated changelog
  * Improved dicttoxml (#121)
  * Added correct badge
  * Started using codecov
  * Fixed flake8 tests
  * Added coverage to the mix
  * Fixed lint issues and CI
  * Checked new CI stuff like lint and coverage
  * Bumped version and generated changelog
  * Fixed issue with wrong output for boolean list
  * Made pull requests trigger action runs

3.18.0 / 2022-04-23
===================

  * Bumped version
  * Improved dicttoxml (#121)
  * Added correct badge
  * Started using codecov
  * Fixed flake8 tests
  * Added coverage to the mix
  * Fixed lint issues and CI
  * Checked new CI stuff like lint and coverage
  * Bumped version and generated changelog
  * Fixed issue with wrong output for boolean list
  * Made pull requests trigger action runs

3.17.1 / 2022-04-20
===================

  * Fixed issue with wrong output for boolean list
  * Made pull requests trigger action runs

3.17.0 / 2022-04-18
===================

  * Fixed return of correct xml type for bool (#119)
  * Added download counter
  * Checked latest alpha (#116)
  * Checked latest alpha (#115)
  * Updated waitress from 2.0.0 to 2.1.1 in /docs (#114)
  * Only python3 wheels are created now

3.15.0 / 2022-02-24
===================

  * Merged remote-tracking branch 'origin/master'
  * Bumped version and prepared for new release
  * Added new python versions to test against (#110)
  * Fixed perflint (#109)
  * Supported latest version of 3.10 and 3.11 alpha3 (#98)
  * Generated changelog
  * Removed unused imports
  * Bumped version
  * Fixed issue with uncaught UnicodeDecodeError
  * Cancelled jobs for concurrent builds in same PR
  * Stabilized pypi
  * Updated tox config

v3.14.0 / 2022-02-10
====================

  * Removed unused imports
  * Bumped version
  * Fixed issue with uncaught UnicodeDecodeError
  * fix: remove unused imports
  * bump version
  * fix: issue with uncaught UnicodeDecodeError
  * cancel jobs for concurrent builds in same PR
  * pypi is stable now
  * feat: update tox config

v3.11.0 / 2022-01-31
====================

  * bump version
  * feat: remove comments
  * Feat: install pytest separately and run pytests now
  * fix tox
  * add some documentation on testing
  * split testing libs away from release
  * fix: update changelog
  * bump version to 3.10.0
  * fix: we support Python3.7+ now (#101)
  * Issue: #99 dicttoxml igores the root param (#100)

v3.10.0 / 2022-01-29
====================

  * bump version to 3.10.0
  * fix: we support Python3.7+ now (#101)
  * Issue: #99 dicttoxml igores the root param (#100)
  * feat: bump to a rc1 version
  * Add support for Python3.11 alpha and upgrade pytest and py (#97)
  * Feat: drop 3.11.0 alphas from the test matrix for now
  * feat: find the versions that are in the CI
  * fix: typo in the name of python 3.11 version
  * sunsetting python 3.6 and add support for python3.11 alpha
  * chore: prepare for release 3.9.0
  * fix email
  * fix readme
  * - update readme - add tests - refactor
  * resolve #93
  * chore: run black on readme doc
  * fix: more issues
  * fix: garbage in history
  * feat: generate history

v3.9.0 / 2021-12-19
===================

  * feat: generate history
  * feat: item_wrap for str and int (#93)

v3.8.4 / 2021-10-24
===================

  * bump version
  * fix: version bump and readme generator

v3.8.3 / 2021-10-24
===================

  * bump version
  * feat: reproduce the error in the test (#90)
  * Feat/version (#88)
  * Feat/docs theme change (#87)
  * Feat/docs theme change (#86)
  * Feat/docs theme change (#85)
  * Feat/docs theme change (#84)
  * Feat/docs theme change (#83)
  * feat: update the docs theme (#82)

v3.8.0 / 2021-10-07
===================

  * Feat/security improvements (#81)
  * :arrow_up: feat: python 3.10 released (#79)

v3.7.0 / 2021-09-11
===================

  * :bookmark: feat: final release for v3.7.0
  * :bookmark: feat: bump version

v3.7.0beta2 / 2021-09-10
========================

  * Feat/cleanup and deprecation fix (#78)
  * item ommision (#76)
  * Create FUNDING.yml

v3.7.0beta1 / 2021-08-28
========================

  * Feat/fork and update dict2xml (#75)
  * chore(deps-dev): bump pip from 18.1 to 19.2 (#73)
  * Delete .travis.yml
  * chore(deps-dev): bump lxml from 4.6.2 to 4.6.3 (#68)
  * Bump lxml from 4.1.1 to 4.6.2 (#66)

v3.6.0 / 2020-11-12
===================

  * Feat/wip exceptions (#65)
  * Add .deepsource.toml
  * feat: upgrade the actions
  * feat: try & support more os and python versions
  * Update pythonpackage.yml

v3.5.0 / 2020-08-24
===================

  * feat: remove six as dependency as we are python3 only, resolves #60 (#61)
  * feat: update makefile for the correct command

v3.4.1 / 2020-06-10
===================

  * fix: issues with pypi release and bump version
  * Feat/attr type docs (#58)
  * fix: conflicts
  * Feat/attr type docs (#57)
  * Merge github.com:vinitkumar/json2xml
  * Update json2xml.py (#56)
  * Merge github.com:vinitkumar/json2xml
  * feat: fix typo in the readme

v3.3.3 / 2020-02-05
===================

  * Update README.rst
  * fix: issue with pypi uploads
  * fix: version
  * bump version
  * Update pythonpackage.yml
  * Refactor/prospector cleanup (#50)
  * Update pythonpackage.yml
  * Create pythonpackage.yml
  * Update README.rst
  * fix: typo in readme
  * bump version
  * Feature/attribute support (#48)
  * Feature/attribute support (#47)
  * chore: bump version
  * fix: remove print statement in json read because it confuses people
  * fix typo in readme

v3.0.0 / 2019-02-26
===================

  * Fix/coveralls (#43)
  * update coverage report (#42)
  * Merge pull request #41 from vinitkumar/fix/coveralls
  * add python coveralls
  * Merge pull request #40 from vinitkumar/refactor/cookiecutter
  * update coverage
  * add image for coveralls
  * coverage and coveralls integrations
  * try and trigger coveralls too
  * fix code block in readme
  * add doc about custom wrapper
  * try at reducing the dependencies
  * add tests for custom wrappers as well
  * add tests for actualy dict2xml conversion
  * fix: remove missing import
  * fix: code syntax highlight in the readme again
  * fix: code syntax highlight in the readme again
  * fix: code syntax highlight in the readme
  * chore: update readme with code samples
  * test: add testcases for the different utils method
  * remove unused imports
  * check the third method for generating dict from json string too
  * run correct test files
  * fix tests
  * update requirements and setuptools
  * refactor the module into more maintainable code
  * chore: add boilerplate
  * remove all legacy
  * Fix/cleanup (#38)
  * cleanup: remove unused modules (#37)
  * Merge pull request #35 from vinitkumar/improve-structure
  * cleanup
  * one again try to get the build working
  * travis need full version for latest supported python
  * do not hardcode version in a series
  * update grammar
  * fix conflicts
  * Update LICENSE
  * cleanup readme
  * remove cli
  * some cleanup and update the tests
  * Update readme.md
  * Cleanup Readme.md
  * Update issue templates
  * fix vulnerabilities in requests

