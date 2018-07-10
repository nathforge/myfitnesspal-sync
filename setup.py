from setuptools import setup, find_packages

setup(
    name='mfpsync',
    version='0.13',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    license='LICENSE.txt',
    description='Unofficial MyFitnessPal sync API client',
    long_description=open('README.rst').read(),
    author='Nathan Reynolds',
    author_email='email@nreynolds.co.uk',
    url='https://github.com/nathforge/mfpsync',
    entry_points={
        'console_scripts': [
            'mfpsync = mfpsync.main:main'
        ]
    },
    zip_safe=True
)
