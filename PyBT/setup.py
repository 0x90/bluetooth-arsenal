from setuptools import setup

setup(
    name = "PyBT",
    version = "0.1",
    author = "Mike Ryan",
    author_email = "mikeryan@lacklustre.net",
    description = ("Bluetooth stack in Python"),
    license = "MIT",
    keywords = "bluetooth ble",
    url = "https://github.com/mikeryan/PyBT",
    packages=['PyBT'],
    install_requires = ['scapy'],
    entry_points = {
        'console_scripts': [
            'gatt_client = PyBT.gattclient:main',
        ],
    },
    extras_require = {
        'gattclient': ['gevent'],
    }
)
