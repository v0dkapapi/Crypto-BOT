from setuptools import setup, find_packages

setup(
    name="crypto_assistant",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'streamlit',
        'pandas',
        'numpy',
        'requests',
        'python-dotenv',
        'plotly',
        'pandas-ta',
        'alpha_vantage'
    ],
)