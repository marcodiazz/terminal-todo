from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="terminal-todo",
    version="1.0.0",
    author="Marco Diaz",
    description="A beautiful terminal-based todo app built with Textual",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/marcodiazz/terminal-todo",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "textual>=6.9.0",
    ],
    entry_points={
        "console_scripts": [
            "todo=terminal_todo.app:main",
        ],
    },
    include_package_data=True,
    package_data={
        "terminal_todo": ["*.tcss"],
    },
)
