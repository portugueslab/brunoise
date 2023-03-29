from distutils.core import setup
from setuptools import find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="bruoise",
    version="0.1.1",
    author="Vilim Stih, Emanuele Paoli, Diego Asua, You Kure Wu, Nathan van Beelen @ Portugueslab",
    author_email="vilim@neuro.mpg.de",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="imaging microscopy 2-photon",
    description="A user-friendly software for efficient control of two-photon microscopes.",
    entry_points={
        "console_scripts": [
            "brunoise=brunoise.main:main",
        ]
    },
)
