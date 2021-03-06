# leicaautomator

[![build-status-image]][travis]
[![pypi-version]][pypi]
[![wheel]][pypi]


## Overview

Automate scans on Leica SPX microscopes

## Requirements

* Python (2.7, 3.4)

## Installation

Install using `pip`...

```bash
pip install leicaautomator
```

TODO: note about qt


**Mac users:**
Run PySide post install:
```bash
pyside_postinstall.py -install
```

## Example

![](demo.png)

## Documentation
Read API reference: http://leicaautomator.rtfd.org/

## Development
Install dependencies and link development version of leicaautomator to pip:
```bash
git clone https://github.com/arve0/leicaautomator
cd leicaautomator
pip install -r requirements.txt
```

#### run test
```bash
tox
```

#### extra output, jump into pdb upon error
```bash
tox -- -s --pdb
```

#### build api reference
```bash
pip install -r docs/requirements.txt
make docs
```


[build-status-image]: https://secure.travis-ci.org/arve0/leicaautomator.png?branch=master
[travis]: http://travis-ci.org/arve0/leicaautomator?branch=master
[pypi-version]: https://img.shields.io/pypi/v/leicaautomator.svg
[pypi]: https://pypi.python.org/pypi/leicaautomator
[wheel]: https://img.shields.io/pypi/wheel/leicaautomator.svg
