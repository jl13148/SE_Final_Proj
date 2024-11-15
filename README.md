# SE_Final_Proj

Code based on [flask-boilerplate](https://github.com/realpython/flask-boilerplate.git)

## Starting the Webpage

1. **Clone the repository**
    ```bash
    git clone https://github.com/jl13148/SE_Final_Proj.git
    cd SE_Final_Proj/flask-boilerplate
    ```

2. **Initialize and activate a virtual environment**
    ```bash
    conda create -n <venv-name> python=3.8
    conda activate <venv-name>
    ```

3. **Install the dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4. **Run the development server**
    ```bash
    python app.py
    ```
    or
    ```bash
    flask run
    ```

5. **Navigate to the application**
    Open your web browser and go to [http://localhost:5000](http://localhost:5000)

## Testing

To ensure that the application is functioning correctly, follow these steps to run the test suite and generate a coverage report:

1. **Navigate to the flask-boilerplate directory**
    ```bash
    cd flask-boilerplate
    ```

2. **Run the tests with coverage**
    ```bash
    coverage run test_app.py
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
