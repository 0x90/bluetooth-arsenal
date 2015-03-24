#BTScan
Bluetooth-based wireless positioning.

##Dependencies
- Matplotlib (python-matplotlib)
- PyQT4 (python-qt4)
- MySQLDB (python-mysqldb)
- NLMaP (see ./lib/)
- PIL (python-imaging)

##Usage
`btscan.c` contains the receiver code, which forwards timestamped RSSI data over the network to a central server.  `scan_server.py` contains a the server code, which provides an asynchronous pipeline-based framework for data analysis.  `data_generator.py` provides utilities for test data generation, and `tracking_method.py` implements most of the actual tracking algorithms.

To run the GUI with the default testing configuration (defined in `config.py`), run `tracking_pyqt.py`.
