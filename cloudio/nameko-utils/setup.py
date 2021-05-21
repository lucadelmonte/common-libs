import setuptools

setuptools.setup(
    name='nameko-utils',
    version='0.1',
    packages=setuptools.find_packages(),
    install_requires=[
        'json-logging>=1.3.0,<1.4',
        'nameko>=2.13.0,<2.14'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
