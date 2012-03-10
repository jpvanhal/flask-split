from setuptools import setup


setup(
    name='Flask-Split',
    version='0.1.0',
    url='http://github.com/jpvanhal/flask-split',
    license='BSD',
    author='Janne Vanhala',
    author_email='janne.vanhala@gmail.com',
    description='A/B testing for your Flask application',
    packages=['flask_split'],
    zip_safe=False,
    platforms='any',
    install_requires=[
        'Flask',
        'Redis >= 2.0'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
