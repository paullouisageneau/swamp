from setuptools import setup


def read_file(path):
    with open(path) as file:
        return file.read()


setup(
    name="swamp",
    version="0.1.0",
    description="Swamp",
    long_description=read_file("README.rst"),
    url="TODO",
    author="Paul-Louis Ageneau",
    author_email="paul-louis@ageneau.org",
    license="GNU Affero General Public License v3 or later (AGPLv3+)",
    packages=["swamp"],
    include_package_data=True,
    zip_safe=False,
    entry_points={"console_scripts": ["swamp=app.__main__:main"]},
    install_requires=["flask >= 0.12.1", "gevent >= 1.2.1"],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
    ],
)
