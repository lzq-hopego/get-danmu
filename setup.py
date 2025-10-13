import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="get_danmu",
    version="0.3.2",
    author="Li Zhan Qi",
    author_email="3101978435@qq.com",
    description="可以下载弹幕的包哦",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    project_urls={
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Environment :: Console", 
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "flask",
        "flask_sqlalchemy",
        "protobuf",
        "requests",
        "rich",
        "sqlalchemy",
        "ujson",
        "xmltodict"
    ],
    entry_points={
        'console_scripts': ["get-danmu=get_danmu.__main__:main",
                            "get-dm=get_danmu.__main__:main"
            ],
    },
)
