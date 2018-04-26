from setuptools import setup

setup(name='meleedat2json',
    version='0.1',
    description='Reads Melee .dat files and dumps character data to JSON',
    url='https://github.com/pfirsich/meleeDat2Json',
    author='Joel Schumacher',
    author_email='',
    license='MIT',
    packages=['meleedat2json'],
    install_requires=[
      'bitstruct',
    ],
    entry_points = {
        'console_scripts': ['meleedat2json=meleedat2json:main'],
    },
    zip_safe=False)
