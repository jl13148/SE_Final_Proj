# SE_Final_Proj
DiabetesEase
![Coverage](.github/badges/coverage.svg)

Code based on [flask-boilerplate](https://github.com/realpython/flask-boilerplate.git)

## Documentation
- [User Guide](USER_GUIDE.md) - Detailed instructions for using DiabetesEase

## Starting the Webpage

1. **Clone the repository**
    ```bash
    git clone https://github.com/jl13148/SE_Final_Proj.git
    cd SE_Final_Proj/project
    ```

2. **Initialize and activate a virtual environment**
    ```bash
    conda create -n <venv-name> python=3.9
    conda activate <venv-name>
    ```

3. **Install the dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4. **Initialize the database**
    ```bash
    python manage.py init-db
    python manage.py reset-db
    ```

5. **Run the development server**
    ```bash
    python run.py
    ```

6. **Navigate to the application**
    Open your web browser and go to [http://localhost:5000](http://localhost:5000)

## Testing

To ensure that the application is functioning correctly, follow these steps to run the test suite and generate a coverage report:

1. **Run the tests with coverage**
    ```bash
    coverage run -m unittest discover tests
    ```

2. **Show the coverage report in the terminal**
    ```bash
    coverage report -m
    ```

3. **Generate the coverage report in HTML format**
    ```bash
    coverage html
    ```

4. **View the coverage report**
    Open the generated `htmlcov/index.html` file in your web browser to see detailed coverage information.

    ```bash
    open htmlcov/index.html
    ```
    *Note: The `open` command works on macOS. For Windows, use `start htmlcov\index.html`, and for Linux, use `xdg-open htmlcov/index.html`.*
