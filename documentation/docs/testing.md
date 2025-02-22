
## Testing
This project uses `pytest`. 

### Running Tests with Coverage

This project uses `coverage.py` to measure test coverage for the codebase.

#### **Prerequisites**
Ensure you have `coverage` and `pytest` installed. If not, manually install them using or run `pip install -r requirements.txt` in your virtual environment:

```sh
pip install coverage pytest
```

#### **Running Tests with Coverage**
To run tests located in the `tests/` folder while tracking coverage, run the following in the `bountyagent/` folder:

```sh
coverage run --rcfile=.coveragerc -m pytest tests/
```

#### **Generating Coverage Reports**
After running the tests, generate coverage reports using the following commands:

##### 1. **View Coverage Summary in the Terminal**
```sh
coverage report
```

##### 2. **Generate an HTML Coverage Report**
For a visual representation, run:

```sh
coverage html
```

Then, open `htmlcov/index.html` in your browser to view the detailed coverage report by doing the following: 
```sh
open htmlcov/index.html
```

#### **Enforcing Minimum Coverage**
To enforce a minimum test coverage percentage (e.g., 80%), use:

```sh
coverage report --fail-under=80
```

This command will cause the process to fail if the coverage is below 80%.

---

For further details on `coverage.py`, refer to the official documentation: [Coverage.py](https://coverage.readthedocs.io/)
