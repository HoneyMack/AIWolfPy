import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="aiwolfpy", # Replace with your own username
    version="0.0.1",
    install_requires=[
        "numpy", "scipy", "pandas"
    ],
    author="Kei Harada",
    description="python agents that can play Werewolf, following the specifications of the AIWolf Project",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aiwolf/AIWolfPy",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)